from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from app.forms import RegistrationForm, LoginForm
from app.models import User
from app import db
from flask import session

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    print("ERRORI:", form.errors)
    if form.validate_on_submit():

        # accetta solo CLIENTE o FORNITORE
        ruolo_scelto = form.ruolo.data.upper()
        if ruolo_scelto not in ["CLIENTE", "FORNITORE"]:
            ruolo_scelto = "CLIENTE"

        user = User(
            username=form.username.data,
            email=form.email.data,
            ruolo=ruolo_scelto
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registrazione completata!')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():

    session.pop('cart', None)

    # Se è già loggato → mandalo alla dashboard giusta
    if current_user.is_authenticated:
        if current_user.ruolo == "ADMIN":
            return redirect(url_for('main.dashboard_admin'))
        elif current_user.ruolo == "FORNITORE":
            return redirect(url_for('main.dashboard_fornitore'))
        else:
            return redirect(url_for('main.dashboard_cliente'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Accesso effettuato!')

            # Redirect in base al ruolo
            if user.ruolo == 'ADMIN':
                return redirect(url_for('main.dashboard_admin'))
            elif user.ruolo == 'FORNITORE':
                return redirect(url_for('main.dashboard_fornitore'))
            else:
                return redirect(url_for('main.dashboard_cliente'))

        flash('Credenziali non valide')

    return render_template('auth/login.html', form=form)


@auth.route('/logout')

def logout():
    session.pop('cart', None)
    logout_user()
    return redirect(url_for('main.home'))