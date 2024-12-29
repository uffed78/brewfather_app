# File: routes.py
# Flask-relaterade imports
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required

# Verktyg och säkerhet
from werkzeug.security import generate_password_hash, check_password_hash

# Egna moduler
from models import User, db
from helpers import generate_openai_recipe, fetch_inventory

from flask_login import login_required, current_user

# Övriga moduler
import requests
import base64
import os


routes = Blueprint('routes', __name__)

BREWFATHER_API_BASE_URL = "https://api.brewfather.app/v2/inventory"
BREWFATHER_USERNAME = os.getenv("BREWFATHER_USERNAME")
BREWFATHER_API_KEY = os.getenv("BREWFATHER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@routes.route('/')
def home():
    return render_template('index.html')

from flask_login import login_required, current_user

@routes.route('/inventory/<category>', methods=['GET'])
@login_required
def get_inventory(category):
    # Validera kategorin
    valid_categories = ['fermentables', 'hops', 'yeasts']
    if category not in valid_categories:
        return jsonify({"error": f"Invalid category. Must be one of {valid_categories}"}), 400

    # Kontrollera om den inloggade användaren har sparade Brewfather-uppgifter
    if not current_user.brewfather_username or not current_user.brewfather_api_key:
        return jsonify({"error": "No Brewfather credentials provided. Please update your settings."}), 400

    # Generera Basic Auth header baserat på användarens uppgifter
    auth_string = f"{current_user.brewfather_username}:{current_user.brewfather_api_key}"
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

    # Gör API-förfrågan
    url = f"https://api.brewfather.app/v2/inventory/{category}"
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": response.text}), response.status_code


@routes.route('/generate_recipe', methods=['POST'])
def generate_recipe():
    inventory = request.json.get('inventory', [])
    measurement = request.json.get('measurement', 'metric')
    use_inventory = request.json.get('use_inventory', True)
    beer_style = request.json.get('beer_style', 'any')

    if use_inventory:
        prompt = f"Based on this inventory: {inventory}, generate a beer recipe."
    else:
        prompt = f"Generate a beer recipe without inventory constraints."

    if beer_style != 'any':
        prompt += f" The beer style should be {beer_style}."
    prompt += f" Use {measurement} measurements."

    result = generate_openai_recipe(prompt)
    if isinstance(result, tuple):  # Om det är ett fel
        return jsonify(result[0]), result[1]
    return jsonify({"recipe": result})

@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Kontrollera om användaren redan finns
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('routes.register'))

        try:
            # Hasha lösenordet och skapa användaren
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful!', 'success')
            return redirect(url_for('routes.login'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('routes.register'))

    return render_template('register.html')


@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Hämta användaren från databasen
        user = User.query.filter_by(username=username).first()

        # Kontrollera att användaren finns och lösenordet är korrekt
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('routes.home'))
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html')

@routes.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Hämta uppgifter från formuläret
        brewfather_username = request.form['brewfather_username']
        brewfather_api_key = request.form['brewfather_api_key']

        # Uppdatera användarens Brewfather-uppgifter
        current_user.brewfather_username = brewfather_username
        current_user.brewfather_api_key = brewfather_api_key
        db.session.commit()

        flash('Settings updated successfully!', 'success')
        return redirect(url_for('routes.settings'))

    return render_template('settings.html')

from flask import request, jsonify
from openai import OpenAI
import os

# Ladda API-nyckeln från miljövariabeln
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@routes.route('/interactive_session', methods=['POST'])
def interactive_session():
    # Hämta användarens meddelande och chattens historik
    user_message = request.json.get('user_message')
    chat_history = request.json.get('chat_history', [])

    # Kontrollera att API-nyckeln är konfigurerad
    if not OPENAI_API_KEY:
        return jsonify({"error": "Servern saknar en API-nyckel"}), 500

    # Skapa en klient med API-nyckeln
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Förbered historiken för OpenAI
    formatted_messages = [
        {"role": message["role"], "content": message["content"]}
        for message in chat_history
    ]
    formatted_messages.append({"role": "user", "content": user_message})

    try:
        # Anropa OpenAI API via klienten
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=formatted_messages
        )

        # Hämta GPT:s svar
        gpt_response = response['choices'][0]['message']['content']
        chat_history.append({"role": "assistant", "content": gpt_response})

        return jsonify({"response": gpt_response, "chat_history": chat_history})

    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return jsonify({"error": str(e)}), 500


@routes.route('/interactive', methods=['GET'])
def interactive():
    return render_template('interactive.html')

@routes.route('/interactive_session', methods=['POST'])
def interactive_session():
    from openai import OpenAI
    import os

    # Ladda API-nyckeln från miljövariabeln
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Hämta data från request
    user_message = request.json.get('user_message')
    chat_history = request.json.get('chat_history', [])

    if not OPENAI_API_KEY:
        return jsonify({"error": "Servern saknar API-nyckel"}), 500

    # Förbered historiken
    formatted_messages = [
        {"role": message["role"], "content": message["content"]}
        for message in chat_history
    ]
    formatted_messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=formatted_messages
        )

        gpt_response = response['choices'][0]['message']['content']
        chat_history.append({"role": "assistant", "content": gpt_response})

        return jsonify({"response": gpt_response, "chat_history": chat_history})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
