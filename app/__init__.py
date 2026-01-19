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


mail = Mail()
db = SQLAlchemy()
migrate = Migrate()

login_manager = LoginManager()
login_manager.login_view = "auth.login"

limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[]
    )

def create_app():
    app = Flask(__name__)
    limiter.init_app(app)
    

    # Carica la configurazione
    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[env])

    # 🔥 AGGIUNGI QUESTA RIGA
    app.config['STRIPE_WEBHOOK_SECRET'] = os.environ.get('STRIPE_WEBHOOK_SECRET')

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
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return None
        user = User.query.get(user_id)
        return user

    # Blueprint
    from app.auth.routes import auth
    app.register_blueprint(auth)

    from app.webhook import webhook_bp
    app.register_blueprint(webhook_bp)

    from app.routes import main
    app.register_blueprint(main)

    

    return app