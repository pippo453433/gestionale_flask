from itsdangerous import URLSafeTimedSerializer

from flask import current_app

def genera_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt="email-confirm")

def verifica_token(token, max_age=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.loads(token, salt="email-confirm", max_age=max_age)