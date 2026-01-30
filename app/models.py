from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------
# TABELLA DI ASSOCIAZIONE FORNITORE ↔ PRODOTTO
# (User con ruolo FORNITORE)
# ---------------------------------------------------------
fornitore_prodotto = db.Table(
    'fornitore_prodotto',
    db.Column('fornitore_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('prodotto_id', db.Integer, db.ForeignKey('prodotto.id'), primary_key=True)
)

# ---------------------------------------------------------
# MODELLO USER (CLIENTE / FORNITORE / ADMIN)
# ---------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    ruolo = db.Column(db.String(20), nullable=False, default="CLIENTE")  # CLIENTE, FORNITORE, ADMIN
    # Campi aziendali (solo per fornitori)
    company_name = db.Column(db.String(120))
    partita_iva = db.Column(db.String(20))
    indirizzo_azienda =db.Column(db.String(200))
    telefono_azienda = db.Column(db.String(20))

    ragione_sociale = db.Column(db.String(100))
    partita_iva = db.Column(db.String(20))
    telefono = db.Column(db.String(20))
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    email_verificata = db.Column(db.Boolean, default=False)

    # Relazione molti-a-molti con Prodotto
    prodotti = db.relationship(
        'Prodotto',
        secondary=fornitore_prodotto,
        back_populates='fornitori'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ---------------------------------------------------------
# MODELLO CATEGORIA
# ---------------------------------------------------------
class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descrizione = db.Column(db.Text)
    attiva = db.Column(db.Boolean, default=True)

    prodotti = db.relationship('Prodotto', backref='categoria', lazy=True)

# ---------------------------------------------------------
# MODELLO PRODOTTO
# ---------------------------------------------------------
class Prodotto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codice = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text)
    prezzo = db.Column(db.Numeric(10, 2), nullable=False)
    quantita = db.Column(db.Integer, default=0)
    attivo = db.Column(db.Boolean, default=True)

    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)

    # Relazione inversa con User (fornitori)
    fornitori = db.relationship(
        'User',
        secondary=fornitore_prodotto,
        back_populates='prodotti'
    )


class Ordine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data_ordine = db.Column(db.DateTime, default=datetime.utcnow)
    stato = db.Column(db.String(20), default='PENDING')  # PENDING, CONFERMATO, SPEDITO, CONSEGNATO
    totale = db.Column(db.Numeric(10, 2), default=0)
    note = db.Column(db.Text)
    cliente = db.relationship('User', backref='ordini')
    dettagli = db.relationship('OrdineDettaglio', backref='ordine', cascade="all, delete-orphan")
    nome = db.Column(db.String(100))
    cognome = db.Column(db.String(100))
    indirizzo = db.Column(db.String(200))
    citta = db.Column(db.String(100))
    cap = db.Column(db.String(20))
    provincia = db.Column(db.String(100))
    telefono = db.Column(db.String(30))
    email = db.Column(db.String(100))
    pagato = db.Column(db.Boolean, default=False)
    stripe_session_id = db.Column(db.String(100))
    stripe_payment_intent = db.Column(db.String(255))

class OrdineDettaglio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ordine_id = db.Column(db.Integer, db.ForeignKey('ordine.id'), nullable=False)
    prodotto_id = db.Column(db.Integer, db.ForeignKey('prodotto.id'), nullable=False)
    quantita = db.Column(db.Integer, nullable=False)
    prezzo_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    prodotto = db.relationship('Prodotto')

    @property
    def subtotale(self):
        return self.quantita * self.prezzo_unitario
