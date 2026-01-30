import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
import stripe
from config import config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect

mail = Mail()
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

login_manager = LoginManager()
login_manager.login_view = "auth.login"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[]
)

def create_app():

    app = Flask(__name__)
    limiter.init_app(app)
    csrf.init_app(app)

    # Carica configurazione
    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[env])

    # Stripe webhook secret
    app.config['STRIPE_WEBHOOK_SECRET'] = os.environ.get('STRIPE_WEBHOOK_SECRET')

    # Chiave Stripe
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
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return None
        return User.query.get(user_id)

    # Blueprint autenticazione
    from app.auth.routes import auth
    app.register_blueprint(auth)

    # 🔥 IMPORTA LA FUNZIONE DEL WEBHOOK (NON IL BLUEPRINT)
    from app.webhook import stripe_webhook

    # 🔥 DISATTIVA CSRF SOLO PER QUESTA FUNZIONE
    csrf.exempt(stripe_webhook)

    # 🔥 REGISTRA LA ROUTE MANUALMENTE
    app.add_url_rule('/webhook', view_func=stripe_webhook, methods=['POST'])

    # Blueprint principale
    from app.routes import main
    app.register_blueprint(main)

    return app