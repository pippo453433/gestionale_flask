import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'data', 'gestionale.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # STRIPE
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

    # SENDGRID
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

    # COOKIE SECURITY
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # True solo in produzione
    REMEMBER_COOKIE_HTTPONLY = True

    # SESSIONE
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # CSRF (se usi Flask-WTF)
    WTF_CSRF_ENABLED = True

    # JSON
    JSONIFY_PRETTYPRINT_REGULAR = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class DevelopmentConfig(Config):
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    DEBUG = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}