from flask import Flask, request, jsonify
import sqlite3
import pandas as pd
from sklearn.preprocessing import LabelEncoder

app = Flask(__name__, static_folder='static')

# Load the product data from SQLite database
def load_products():
    conn = sqlite3.connect('rituals.db')
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return products_df

# Load products data
products_df = load_products()

# Define the categorize functions
def categorize_scent(description):
    if pd.isna(description):
        return 'Other'
    description_lower = description.lower()
    if any(keyword in description_lower for keyword in ['floral', 'flower', 'blossom', 'rose', 'peony', 'lotus']):
        return 'Floral'
    elif any(keyword in description_lower for keyword in ['fresh', 'mint', 'eucalyptus', 'tea', 'white tea', 'green tea', 'citrus', 'orange']):
        return 'Fresh'
    elif any(keyword in description_lower for keyword in ['oriental', 'spice', 'oudh', 'patchouli', 'incense', 'amber']):
        return 'Oriental'
    else:
        return 'Other'

def categorize_usage(subcategory):
    if pd.isna(subcategory):
        return 'Other'
    if 'Bath' in subcategory:
        return 'Bath'
    elif 'Shower' in subcategory:
        return 'Shower'
    elif any(word in subcategory for word in ['Oil', 'Scrub', 'Cream', 'Lotion']):
        return 'Oil'
    else:
        return 'Other'

def categorize_effect(description):
    if pd.isna(description):
        return 'Other'
    description_lower = description.lower()
    if any(keyword in description_lower for keyword in ['relax', 'calm', 'sleep', 'soothing', 'tranquility', 'peaceful', 'balance']):
        return 'Relaxing'
    elif any(keyword in description_lower for keyword in ['energize', 'vitality', 'refresh', 'revitalize', 'invigorate', 'stimulate']):
        return 'Energizing'
    elif any(keyword in description_lower for keyword in ['detox', 'purify', 'cleanse', 'clarify', 'exfoliate']):
        return 'Detoxifying'
    else:
        return 'Other'

# Apply the functions to create new columns
products_df['Scent'] = products_df['Description'].apply(categorize_scent)
products_df['Usage'] = products_df['Subcategory'].apply(categorize_usage)
products_df['Effect'] = products_df['Description'].apply(categorize_effect)

# Initialize and fit the encoders with all possible classes
le_scent = LabelEncoder()
le_usage = LabelEncoder()
le_effect = LabelEncoder()

# Fit with all possible categories (including those that might come from user input)
le_scent.fit(['Floral', 'Fresh', 'Oriental', 'Other'])
le_usage.fit(['Bath', 'Shower', 'Oil', 'Other'])
le_effect.fit(['Relaxing', 'Energizing', 'Detoxifying', 'Other'])

# Encode product features
products_df['Scent_encoded'] = le_scent.transform(products_df['Scent'])
products_df['Usage_encoded'] = le_usage.transform(products_df['Usage'])
products_df['Effect_encoded'] = le_effect.transform(products_df['Effect'])

# Safe transform function to avoid unseen label errors
def safe_transform(encoder, value, default_value='Other'):
    if value in encoder.classes_:
        return encoder.transform([value])[0]
    else:
        print(f"Warning: '{value}' not seen during fit, using default value '{default_value}'")
        return encoder.transform([default_value])[0]

# The enhanced recommendation function with weighted attributes
def recommend_products(user_preferences, products_df):
    # Use safe_transform to avoid unseen label errors
    user_scent = safe_transform(le_scent, user_preferences['preferred_scent'])
    user_usage = safe_transform(le_usage, user_preferences['usage'])
    user_effect = safe_transform(le_effect, user_preferences['desired_effect'])

    # Assign weights to attributes (adjust as needed)
    weights = {
        'Scent': 0.5,
        'Usage': 0.3,
        'Effect': 0.2
    }

    # Calculate weighted similarity
    products_df['similarity'] = (
        (products_df['Scent_encoded'] == user_scent).astype(int) * weights['Scent'] +
        (products_df['Usage_encoded'] == user_usage).astype(int) * weights['Usage'] +
        (products_df['Effect_encoded'] == user_effect).astype(int) * weights['Effect']
    )

    # Sort and return top 3 products with highest similarity
    recommended_products = products_df.sort_values(by=['similarity', 'Price_(EUR)'], ascending=[False, True])
    return recommended_products.head(3)

@app.route('/')
def index():
    return app.send_static_file('rituals_fully_rendered.html')

@app.route('/get_recommendation', methods=['POST'])
def get_recommendation():
    data = request.get_json()

    # Extract customer inputs
    user_preferences = {
        'gender': data['gender'],
        'skin_type': data['skin_type'],
        'preferred_scent': data['preferred_scent'],
        'usage': data['usage'],
        'desired_effect': data['desired_effect']
    }

    # Map numerical inputs back to categorical for encoding
    gender_mapping = {0: 'Male', 1: 'Female', 2: 'Other'}
    skin_type_mapping = {0: 'Dry', 1: 'Oily', 2: 'Sensitive'}
    scent_mapping = {0: 'Floral', 1: 'Fresh', 2: 'Oriental'}
    usage_mapping = {0: 'Bath', 1: 'Shower', 2: 'Oil'}
    effect_mapping = {0: 'Relaxing', 1: 'Energizing', 2: 'Detoxifying'}

    user_preferences['gender'] = gender_mapping.get(int(user_preferences['gender']), 'Other')
    user_preferences['skin_type'] = skin_type_mapping.get(int(user_preferences['skin_type']), 'Other')
    user_preferences['preferred_scent'] = scent_mapping.get(int(user_preferences['preferred_scent']), 'Other')
    user_preferences['usage'] = usage_mapping.get(int(user_preferences['usage']), 'Other')
    user_preferences['desired_effect'] = effect_mapping.get(int(user_preferences['desired_effect']), 'Other')

    # Get recommendations
    recommendations = recommend_products(user_preferences, products_df)

    # Convert the recommendations to a list of dictionaries
    recommended_products = recommendations[['Product_Name', 'Description', 'Price_(EUR)', 'Category', 'Subcategory', 'Collection']].to_dict('records')

    # Return the recommended products as JSON
    return jsonify(recommended_products)

if __name__ == '__main__':
    app.run(debug=True)
