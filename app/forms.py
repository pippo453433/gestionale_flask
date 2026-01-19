from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from wtforms import ValidationError
from wtforms import StringField, DecimalField, IntegerField, TextAreaField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Email





def dominio_valido(form, field):
    email = field.data.lower()
    domini_ammessi = ["gmail.com", "outlook.com", "azienda.it", "hotmail.com", "live.com", "msn.com", "yahoo.com", "icloud.com", "libero.it", "virgilio.it", "tiscali.it"]

    if not any(email.endswith("@" + dominio) for dominio in domini_ammessi):
        raise ValidationError("Dominio email non ammesso.")

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3)])
    email = StringField('Email', validators=[DataRequired(), Email(), dominio_valido])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Conferma Password', validators=[EqualTo('password')])
    ruolo = SelectField(
        'Tipo',
        choices=[
            ('CLIENTE', 'Cliente'),
            ('FORNITORE', 'Fornitore')
        ],
        default='CLIENTE' 
    )
    submit = SubmitField('Registrati')
    def validate_email(self, field):
        from app.models import User
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("Email già registrata.")
    


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Accedi')


class ProdottoForm(FlaskForm):
    codice = StringField('Codice', validators=[DataRequired()])
    nome = StringField('Nome', validators=[DataRequired()])
    descrizione = TextAreaField('Descrizione')
    prezzo = DecimalField('Prezzo', validators=[DataRequired()])
    quantita = IntegerField('Quantità', validators=[DataRequired()])

    # Select categoria (id intero)
    categoria = SelectField('Categoria', coerce=int)

    # Select multipla fornitori (lista di id)
    fornitori = SelectMultipleField('Fornitori', coerce=int)

    submit = SubmitField('Salva')


class ModificaFornitoreForm(FlaskForm):
    ragione_sociale = StringField("Ragione Sociale", validators=[DataRequired()])
    partita_iva = StringField("Partita IVA", validators=[DataRequired()])
    email = StringField("Email", validators=[Email()])
    telefono = StringField("Telefono")
    prodotti = SelectMultipleField("Prodotti associati", coerce=int)
    submit = SubmitField("💾 Salva modifiche")

class CategoriaForm(FlaskForm):
    nome = StringField("Nome Categoria", validators=[DataRequired()])
    submit = SubmitField("Salva")
