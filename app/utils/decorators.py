from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Non loggato
            if current_user.ruolo != role:
                abort(403)  # Non autorizzato
            return f(*args, **kwargs)
        return wrapper
    return decorator

def admin_required(f):

    return role_required("ADMIN")(f)

def fornitore_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        print("DECORATORE ATTIVO:", f.__name__)
        print("DEBUG → autenticato:", current_user.is_authenticated)
        print("DEBUG → ruolo:", getattr(current_user, "ruolo", None))
        if not current_user.is_authenticated:
            abort(401)
        if current_user.ruolo != "FORNITORE":
            abort(403)
        return f(*args, **kwargs)
    return wrapper
    #return role_required("FORNITORE")(f)

def cliente_required(f):

    return role_required("CLIENTE")(f)

#decoratore per accesso a piu ruoli
def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Non loggato
            if current_user.ruolo not in roles:
                abort(403)  # Non autorizzato
            return f(*args, **kwargs)
        return wrapper
    return decorator