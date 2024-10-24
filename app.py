import pandas as pd
import sqlite3
from flask import Flask, request, jsonify, render_template
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import LabelEncoder
import os
import numpy as np

app = Flask(__name__, template_folder='templates')

# Load data from the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'Ritualsproduct.db')

# Using a context manager to ensure the database connection closes
with sqlite3.connect(db_path) as conn:
    # Load products data
    products = pd.read_sql_query("""
        SELECT product_id, product_name, collection_id, gender, description, stock_status
        FROM products
    """, conn)
    print("Products Data Loaded:", products.head())  # Debugging step

    # Load notes data
    notes = pd.read_sql_query("""
        SELECT note_id, product_id, note
        FROM notes
    """, conn)
    print("Notes Data Loaded:", notes.head())  # Debugging step

    # Load collections data
    collections = pd.read_sql_query("""
        SELECT collection_id, collection_name
        FROM collections
    """, conn)
    print("Collections Data Loaded:", collections.head())  # Debugging step

    # Load prices data
    prices = pd.read_sql_query("""
        SELECT price_id, product_id, product_standard_price
        FROM prices
    """, conn)
    print("Prices Data Loaded:", prices.head())  # Debugging step

# Merge products with collections, prices, and notes
df = products.merge(collections, on='collection_id', how='left')
df = df.merge(prices, on='product_id', how='left')
df = df.merge(notes, on='product_id', how='left')
print("Merged DataFrame:", df.head())  # Debugging step

# Preprocessing the data for machine learning
le_gender = LabelEncoder()
le_price_range = LabelEncoder()
le_note = LabelEncoder()

# Clean the price data by removing currency symbols and commas, then convert to float
df['product_standard_price'] = df['product_standard_price'].replace('[^0-9,.]', '', regex=True).str.replace(',', '.').astype(float)

# Define price ranges for encoding
df['price_range'] = df['product_standard_price'].apply(lambda x: 'Low' if x == 17.90 else ('Medium' if x == 49.90 else 'High'))

# Fill missing values
df['gender'] = df['gender'].fillna('Unknown')
df['note'] = df['note'].fillna('Unknown')

# Encoding categorical variables
df['gender_encoded'] = le_gender.fit_transform(df['gender'].str.strip().str.title().fillna('Unknown'))
df['price_range_encoded'] = le_price_range.fit_transform(df['price_range'].fillna('Unknown'))
df['note_encoded'] = le_note.fit_transform(df['note'].str.strip().str.title().fillna('Unknown'))

# Selecting features for recommendation
features = df[['gender_encoded', 'price_range_encoded', 'note_encoded']]

# Initialize and fit NearestNeighbors model
model = NearestNeighbors(n_neighbors=5, algorithm='auto')
model.fit(features)

@app.route('/')
def index():
    return render_template('Rituals_app.html')

@app.route('/get_notes', methods=['POST'])
def get_notes():
    try:
        user_input = request.json
        user_gender = user_input.get('gender', '').strip().title()
        user_price_point = float(user_input.get('pricePoint', 0))

        filtered_products = df[(df['gender'] == user_gender) & (df['product_standard_price'] == user_price_point)]
        available_notes = filtered_products['note'].dropna().unique().tolist()

        if available_notes:
            return jsonify(list(set(available_notes)))
        else:
            return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/get_recommendation', methods=['POST'])
def get_recommendation():
    try:
        user_input = request.json
        user_gender = user_input['gender'].strip().title()
        user_price_point = float(user_input['price_point']) if 'price_point' in user_input else None
        user_notes = [note.strip().title() for note in user_input['note'].split(',')] if 'note' in user_input else []

        # Transform user input using label encoders
        if user_gender in le_gender.classes_:
            gender_encoded = le_gender.transform([user_gender])[0]
        else:
            gender_encoded = le_gender.transform(['Unknown'])[0]

        # Define the appropriate price range
        if user_price_point == 17.90:
            price_range = 'Low'
        elif user_price_point == 49.90:
            price_range = 'Medium'
        elif user_price_point == 54.90:
            price_range = 'High'
        else:
            return jsonify({'message': 'Invalid price input. Please use one of the available price points: 17.90, 49.90, 54.90.'})

        # Transform the price range
        if price_range in le_price_range.classes_:
            price_range_encoded = le_price_range.transform([price_range])[0]
        else:
            price_range_encoded = le_price_range.transform(['Unknown'])[0]

        # Handle multiple notes and find products that match any of the given notes
        note_encoded_list = []
        for note in user_notes:
            if note in le_note.classes_:
                note_encoded_list.append(le_note.transform([note])[0])
            else:
                note_encoded_list.append(le_note.transform(['Unknown'])[0])

        recommendations = []
        for note_encoded in note_encoded_list:
            user_vector = [[gender_encoded, price_range_encoded, note_encoded]]

            # Find nearest neighbors
            distances, indices = model.kneighbors(user_vector)

            # Retrieve recommended products from the original DataFrame
            recommended_products = df.iloc[indices[0]]

            if not recommended_products.empty:
                for _, product in recommended_products.iterrows():
                    recommendations.append({
                        'Product_Name': product['product_name'],
                        'Collection': product['collection_name'],
                        'Notes': product['note'],
                        'Description': product['description'],
                        'Price_(EUR)': product['product_standard_price']
                    })

        unique_recommendations = {rec['Product_Name']: rec for rec in recommendations}.values()

        if unique_recommendations:
            return jsonify(list(unique_recommendations)[:4])
        else:
            return jsonify({'message': 'No products found matching the criteria.'})

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
