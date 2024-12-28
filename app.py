# File: app.py

from flask import Flask, render_template, request, jsonify
import requests
from dotenv import load_dotenv
import os
import base64

# Ladda miljövariabler från .env-filen
load_dotenv()

# Flask setup
app = Flask(__name__)

# API keys och URLs
BREWFATHER_API_BASE_URL = "https://api.brewfather.app/v2/inventory"
BREWFATHER_USERNAME = os.getenv("BREWFATHER_USERNAME")
BREWFATHER_API_KEY = os.getenv("BREWFATHER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/inventory/<category>', methods=['GET'])
def get_inventory(category):
    # Validate category
    valid_categories = ['fermentables', 'hops', 'yeasts']
    if category not in valid_categories:
        return jsonify({"error": f"Invalid category. Must be one of {valid_categories}"}), 400

    # Generate Basic Auth header
    auth_string = f"{BREWFATHER_USERNAME}:{BREWFATHER_API_KEY}"
    auth_base64 = base64.b64encode(auth_string.encode()).decode()

    # Request headers
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/json"
    }

    # Request parameters
    params = {
        "inventory_exists": "true",
        "limit": 50,
        "order_by": "_id",
        "order_by_direction": "asc"
    }

    # Make API request
    url = f"{BREWFATHER_API_BASE_URL}/{category}"
    response = requests.get(url, headers=headers, params=params)

    # Debug log
    print(f"Request Headers: {headers}")
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": response.text}), response.status_code

@app.route('/generate_recipe', methods=['POST'])
def generate_recipe():
    print("POST /generate_recipe hit")

    # Get user options from frontend
    inventory = request.json.get('inventory', [])
    measurement = request.json.get('measurement', 'metric')  # Default to metric
    use_inventory = request.json.get('use_inventory', True)  # Default to using inventory
    beer_style = request.json.get('beer_style', 'any')  # Default to any style

    # Build the prompt
    if use_inventory:
        prompt = f"Based on this inventory: {inventory}, generate a beer recipe."
    else:
        prompt = f"Generate a beer recipe without inventory constraints."

    if beer_style != 'any':
        prompt += f" The beer style should be {beer_style}."

    prompt += f" Use {measurement} measurements."

    print(f"Prompt: {prompt}")

    # Call OpenAI API
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a beer recipe generator."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 200
    }
    print(f"Data sent to OpenAI: {data}")

    response = requests.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers)
    print(f"OpenAI API response status: {response.status_code}")
    print(f"OpenAI API response text: {response.text}")

    if response.status_code == 200:
        recipe = response.json().get("choices")[0].get("message").get("content")
        return jsonify({"recipe": recipe})
    else:
        return jsonify({"error": response.json().get('error').get('message')}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)
