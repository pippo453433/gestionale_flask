import os
from dotenv import load_dotenv
load_dotenv()
from config import config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
import stripe
import os


mail = Mail()
db = SQLAlchemy()
migrate = Migrate()

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)

    # Carica la configurazione in base all'ambiente
    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[env])

    # Imposta la chiave Stripe corretta
    stripe.api_key = app.config['STRIPE_SECRET_KEY']

    # Inizializza estensioni
    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # User loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprint
    from app.auth.routes import auth
    app.register_blueprint(auth)

    from app.webhook import webhook_bp
    app.register_blueprint(webhook_bp)

    from app.routes import main
    app.register_blueprint(main)

    return app