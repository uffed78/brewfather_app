# File: app.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from routes import routes
from models import db, User  # Importera databasmodellen och databashantering

app = Flask(__name__)

# Konfiguration för databasen
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Lägg till en säker hemlig nyckel

# Initiera databasen
db.init_app(app)

# Konfigurera Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'routes.login'  # Om användaren inte är inloggad, skicka dem till login-sidan

# Flask-Login: Ladda användare från databasen
@login_manager.user_loader
def load_user(user_id):
   return db.session.get(User, int(user_id))
# Registrera rutterna från routes.py
app.register_blueprint(routes)

if __name__ == '__main__':
    app.run(debug=True)
