from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.forms import RegistrationForm, LoginForm
from app.models import User
from app import db
from flask import session
from app import limiter
from app.utils.token import genera_token, verifica_token

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register():
    form = RegistrationForm()
    print("ERRORI:", form.errors)

    if form.validate_on_submit():

        # accetta solo CLIENTE o FORNITORE
        ruolo_scelto = form.ruolo.data.upper()
        if ruolo_scelto not in ["CLIENTE", "FORNITORE"]:
            ruolo_scelto = "CLIENTE"
        
        company_name = None
        partita_iva = None
        indirizzo_azienda = None
        telefono_azienda = None

        if ruolo_scelto == "FORNITORE":
            company_name = request.form.get("company_name")
            partita_iva = request.form.get("partita_iva")
            indirizzo_azienda = request.form.get("indirizzo_azienda")
            telefono_azienda = request.form.get("telefono_azienda")

            if not company_name or not partita_iva:
                flash("Per registrarti come fornitore devi compilare tutti i dati aziendali.")
                return redirect(url_for("auth.register"))

        user = User(
            username=form.username.data,
            email=form.email.data,
            ruolo=ruolo_scelto,
            company_name=company_name,
            partita_iva=partita_iva,
            indirizzo_azienda=indirizzo_azienda,
            telefono_azienda=telefono_azienda
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        # 🔥 INVIA EMAIL DI VERIFICA
        from app.email_utils import invia_email_verifica
        invia_email_verifica(user)

        flash('Registrazione completata! Controlla la tua email per confermare l’account.')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
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

            # 🚫 BLOCCA LOGIN SE EMAIL NON VERIFICATA
            if not user.email_verificata:
                flash("Devi confermare la tua email prima di accedere.")
                return redirect(url_for('auth.login'))

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
@limiter.limit("20 per minute")
def logout():
    session.pop('cart', None)
    logout_user()
    return redirect(url_for('main.home'))


@auth.route('/verify/<token>')
def verify_email(token):
    try:
        email = verifica_token(token)
    except:
        flash("Link non valido o scaduto.")
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first_or_404()

    if user.email_verificata:
        flash("Email già verificata. Puoi accedere.")
        return redirect(url_for('auth.login'))

    user.email_verificata = True
    db.session.commit()

    flash("Email verificata con successo! Ora puoi accedere.")
    return redirect(url_for('auth.login'))