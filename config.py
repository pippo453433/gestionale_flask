import os
from dotenv import load_dotenv
load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'gestionale.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # STRIPE
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

    # SENDGRID
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    DEBUG = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}