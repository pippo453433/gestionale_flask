from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail  import Mail
import stripe
import os
from config import config


mail = Mail()
db = SQLAlchemy()       # Istanza globale del database
migrate = Migrate()


login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)         #crea l'app flask
    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[env])   #configurazione base dell'app
    stripe.api_key = app.config['STRIPE_SECRET_KEY']

    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)


    from app.models import User    #importa il blueprint delle rotte
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from app.auth.routes import auth
    app.register_blueprint(auth)

    from app.routes import main
    app.register_blueprint(main)
       

    return app