import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
import joblib

# Load the dataset
df = pd.read_excel('Scraping_Finished.xlsx')

# Define the target variable
target = df['Product_id']

# Drop the target variable from inputs
inputs = df.drop('Product_id', axis='columns')

# Encode categorical features
encoders = {}
for column in inputs.columns:
    if inputs[column].dtype == 'object':
        encoders[column] = LabelEncoder()
        inputs[f"{column}_n"] = encoders[column].fit_transform(inputs[column])

# Select only the encoded columns
inputs_n = inputs[[col for col in inputs.columns if col.endswith('_n')]]

# Train the Decision Tree model
model = DecisionTreeClassifier()
model.fit(inputs_n, target)

# Save the trained model and encoders
joblib.dump(model, 'decision_tree_model.pkl')
joblib.dump(encoders, 'encoders.pkl')

# Function to predict the product based on user input
def predict_product(input_data):
    input_df = pd.DataFrame([input_data])
    
    # Encode the input data
    encoded_input = pd.DataFrame()
    for column, value in input_data.items():
        if column in encoders:
            encoded_value = encoders[column].transform([value])[0]
            encoded_input[f"{column}_n"] = [encoded_value]
    
    # Make the prediction
    prediction = model.predict(encoded_input)[0]
    
    return prediction

# Example usage of the predict_product function
if __name__ == "__main__":
    sample_input = {
        'Gender': 'Male',
        'Notes': 'Woody',
        'Price': 'Medium'
    }
    predicted_product = predict_product(sample_input)
    print(f"Predicted Product ID: {predicted_product}")
