from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(role):
    role = role.upper()  # Normalizza il ruolo richiesto
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Non loggato
            if current_user.ruolo.upper() != role:
                abort(403)  # Non autorizzato
            return f(*args, **kwargs)
        return wrapper
    return decorator

def admin_required(f):
    return role_required("ADMIN")(f)

def fornitore_required(f):
    return role_required("FORNITORE")(f)

def cliente_required(f):
    return role_required("CLIENTE")(f)

def roles_required(*roles):
    # Normalizza tutti i ruoli richiesti in MAIUSCOLO
    roles = [r.upper() for r in roles]
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.ruolo.upper() not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator