import requests
import base64
import os

BREWFATHER_API_BASE_URL = "https://api.brewfather.app/v2/inventory"

def fetch_inventory(category):
    """Hämtar inventariekategorier från Brewfather."""
    BREWFATHER_USERNAME = os.getenv("BREWFATHER_USERNAME")
    BREWFATHER_API_KEY = os.getenv("BREWFATHER_API_KEY")

    # Validera kategori
    valid_categories = ['fermentables', 'hops', 'yeasts']
    if category not in valid_categories:
        return {"error": f"Invalid category. Must be one of {valid_categories}"}, 400

    # Skapa auth-header
    auth_string = f"{BREWFATHER_USERNAME}:{BREWFATHER_API_KEY}"
    auth_base64 = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/json"
    }

    params = {
        "inventory_exists": "true",
        "limit": 50,
        "order_by": "_id",
        "order_by_direction": "asc"
    }

    # Gör API-anropet
    url = f"{BREWFATHER_API_BASE_URL}/{category}"
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}, response.status_code

def generate_openai_recipe(prompt):
    """Anropar OpenAI API för att generera ett ölrecept."""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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

    response = requests.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers)

    if response.status_code == 200:
        return response.json().get("choices")[0].get("message").get("content")
    else:
        return {"error": response.json().get('error').get('message')}, response.status_code
