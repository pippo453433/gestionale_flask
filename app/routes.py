from flask import (
    Blueprint, render_template, flash, request, redirect,
    url_for, jsonify, abort, current_app, session, Response
)
from flask_login import login_user, login_required, current_user, logout_user

from app import db
from app.models import User, Categoria, Prodotto, Ordine, OrdineDettaglio
from app.forms import RegistrationForm, LoginForm, ProdottoForm
from app.utils.decorators import (
    admin_required, fornitore_required, cliente_required, roles_required
)
from app.cart import Cart
from app.email_notifiche import invia_notifica_ordine

import stripe
import csv
from io import StringIO
from datetime import datetime
from .forms import CategoriaForm
from app.forms import SpedizioneForm
from app.utils.token import verifica_token
from app.models import User
from app.forms import ContattiForm
from app.models import Messaggio
from app.forms import RispostaForm
from app.email_utils import send_email
from app.forms import (
    DatiPersonaliForm,
    IndirizziForm,
    PasswordForm,
    PreferenzeForm
)





main = Blueprint('main', __name__)   # crea un blueprint chiamato "main"



# ---------------------------------------------------------
# Funzione  per calcolare le statistiche
# ---------------------------------------------------------
def get_statistiche():
    categorie = Categoria.query.all()
    totale = len(categorie)
    attive = sum(1 for c in categorie if c.attiva)
    non_attive = totale - attive
    percentuale = round((attive / totale) * 100, 1) if totale > 0 else 0
    return totale, attive, non_attive, percentuale

def get_statistiche_prodotti():
    prodotti = Prodotto.query.all()
    totale = len(prodotti)
    attivi = sum(1 for p in prodotti if p.attivo)
    non_attivi = totale - attivi
    valore_totale = sum(p.prezzo * p.quantita for p in prodotti)
    return totale, attivi, non_attivi, valore_totale

# LISTA FORNITORI

@main.route('/fornitori')
def fornitori():
    lista = User.query.filter_by(ruolo="Fornitore").all()
    return render_template('fornitori/fornitori.html', fornitori=lista)

# FORM NUOVO FORNITORE
#@main.route('/fornitore/nuovo', methods=['GET', 'POST'])
#@roles_required("ADMIN", "FORNITORE")
#def nuovo_fornitore():
#    prodotti = Prodotto.query.all()

#    if request.method == 'POST':
#        ragione_sociale = request.form['ragione_sociale']
#        partita_iva = request.form['partita_iva']
#        email = request.form['email']
#        telefono = request.form['telefono']
#        prodotti_ids = request.form.getlist('prodotti')

#        f = Fornitore(
#            ragione_sociale=ragione_sociale,
#            partita_iva=partita_iva,
#            email=email,
#            telefono=telefono
#        )

#        for pid in prodotti_ids:
#            p = Prodotto.query.get(int(pid))
#            f.prodotti.append(p)

#        db.session.add(f)
#        db.session.commit()
#        flash("Fornitore creato con successo", "success")
#        return redirect(url_for('main.fornitori'))

#    return render_template('fornitore_form.html', prodotti=prodotti)

#rotta aggiungi prodotto fornitore
@main.route('/prodotti/nuovo/fornitore', methods=['GET', 'POST'])
@login_required
def prodotto_create_fornitore():
    if current_user.ruolo != 'FORNITORE':
        abort(403)

    form = ProdottoForm()

    if request.method == "POST":
        nuovo_prodotto = Prodotto(
            nome=request.form.get("nome"),
            codice=request.form.get("codice"),
            prezzo=request.form.get("prezzo"),
            quantita=request.form.get("quantita"),
            descrizione=request.form.get("descrizione"),
            categoria_id=request.form.get("categoria_id"),
            attivo=("attivo" in request.form)
        )

        nuovo_prodotto.fornitori.append(current_user)

        db.session.add(nuovo_prodotto)
        db.session.commit()
        flash("Prodotto creato con successo!", "success")
        return redirect(url_for('main.dashboard_fornitore'))

    categorie = Categoria.query.all()
    return render_template('prodotti/aggiungi_prodotto.html', form=form, categorie=categorie)


## rotte carrello
#rotta  per aggiungere carrello
@main.route('/cart/add/<int:id>')
@login_required
def cart_add(id):

    # Impedisce ad ADMIN e FORNITORE di usare il carrello
    if current_user.ruolo != "CLIENTE":
        flash("Solo i clienti possono usare il carrello.", "warning")
        return redirect(url_for('main.prodotti'))

    prodotto = Prodotto.query.get_or_404(id)
    cart = Cart()
    cart.add(prodotto)
    flash(f"{prodotto.nome} aggiunto al carrello!", "success")
    return redirect(request.referrer or url_for('main.prodotti'))

#visualizza carrello
@main.route('/cart', methods=['GET', 'POST'])
@login_required
def cart_view():
    cart = Cart()

    if request.method == 'POST':
        for item in cart.get_items():
            qty_key = f"qty_{item['id']}"
            if qty_key in request.form:
                nuova_qty = int(request.form[qty_key])
                prodotto = Prodotto.query.get(int(item['id']))

                if prodotto and nuova_qty > prodotto.quantita:
                    flash(f"Disponibili solo {prodotto.quantita} per {prodotto.nome}", "warning")
                else:
                    cart.update(item['id'], nuova_qty)

        flash("Quantità aggiornate!", "success")
        return redirect(url_for('main.cart_view'))

    return render_template('carrello/carrello.html', cart=cart)


# Rimuovi prodotto
@main.route('/cart/remove/<int:id>')
@login_required
def cart_remove(id):
    cart = Cart()
    cart.remove(id)
    flash("Prodotto rimosso dal carrello", "info")
    return redirect(url_for('main.cart_view'))

# Svuota carrello
@main.route('/cart/clear')
@login_required
def cart_clear():
    cart = Cart()
    cart.clear()
    flash("Carrello svuotato", "info")
    return redirect(url_for('main.cart_view'))





#route per gestione ordini (admin)
@main.route('/admin/ordini')
@login_required
@admin_required
def gestione_ordini_admin():
    

    stato = request.args.get('stato')
    data_da = request.args.get('data_da')
    data_a = request.args.get('data_a')
    cliente = request.args.get('cliente')

    page = request.args.get('page', 1, type=int)

    query = Ordine.query.join(Ordine.cliente)

    # FILTRO STATO
    if stato and stato != "Tutti":
        query = query.filter(Ordine.stato == stato)

    # FILTRO CLIENTE
    if cliente:
        query = query.filter(db.func.lower(User.username).like(f"%{cliente.lower()}%"))

    # FILTRO DATE
    from datetime import datetime

    if data_da:
        try:
            data_da = datetime.strptime(data_da, "%Y-%m-%d")
            query = query.filter(Ordine.data_ordine >= data_da)
        except ValueError:
            pass

    if data_a:
        try:
            data_a = datetime.strptime(data_a, "%Y-%m-%d")
            query = query.filter(Ordine.data_ordine <= data_a)
        except ValueError:
            pass

    # PAGINAZIONE
    ordini = query.order_by(Ordine.data_ordine.desc()).paginate(page=page, per_page=20)

    # LISTA STATI PER SELECT
    stati = ['PENDING', 'CONFERMATO', 'SPEDITO', 'CONSEGNATO', 'ANNULLATO']

    return render_template(
        'ordini/ordini_admin.html',
        ordini=ordini,
        stati=stati,
        stato_corrente=stato
    )




#Crea ORDINE
@main.route('/ordine/crea', methods=['POST'])
@login_required
def crea_ordine():
    cart = Cart()

    if not cart.cart:
        flash("Il carrello è vuoto.", "warning")
        return redirect(url_for('main.carrello'))

    # 1) CREA L’ORDINE
    nuovo_ordine = Ordine(
        cliente_id=current_user.id,
        email=current_user.email,
        stato="PENDING",
        totale=0,
        note=""
    )

    db.session.add(nuovo_ordine)
    db.session.flush()  # ottieni nuovo_ordine.id

    totale = 0

    for item in cart.get_items():
        dettaglio = OrdineDettaglio(
            ordine_id=nuovo_ordine.id,
            prodotto_id=item.id,
            quantita=item.qty,
            prezzo_unitario=item.price
        )
        db.session.add(dettaglio)
        totale += dettaglio.subtotale

    nuovo_ordine.totale = totale
    db.session.commit()

    # 2) CREA LA SESSIONE STRIPE
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[
            {
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': 'Ordine #' + str(nuovo_ordine.id)},
                    'unit_amount': int(totale * 100),
                },
                'quantity': 1,
            }
        ],
        mode='payment',
        success_url=url_for('main.success', _external=True),
        cancel_url=url_for('main.cancel', _external=True),
        customer_email=current_user.email
    )

    # 3) SALVA L’ID DELLA SESSIONE STRIPE NELL’ORDINE
    nuovo_ordine.stripe_session_id = session.id
    db.session.commit()

    # 4) SVUOTA CARRELLO E REDIRECT AL CHECKOUT
    cart.clear()
    return redirect(session.url)




@main.route('/ordini')
@login_required

def i_miei_ordini():
    ordini = Ordine.query.filter_by(cliente_id=current_user.id).order_by(Ordine.data_ordine.desc()).all()
    return render_template('ordini/ordini_clienti.html', ordini=ordini)

#pulsante dettaglii ordine dashboard_admin
from sqlalchemy.orm import joinedload
@main.route('/ordine/<int:id>')
@login_required
def dettaglio_ordine(id):
    ordine = Ordine.query.options(
        joinedload(Ordine.dettagli).joinedload(OrdineDettaglio.prodotto)
    ).get_or_404(id)

    if ordine.cliente_id != current_user.id and current_user.ruolo != 'ADMIN':
        flash('Accesso negato', 'danger')
        return redirect(url_for('main.i_miei_ordini'))

    return render_template('ordini/ordine_dettaglio.html', ordine=ordine, STRIPE_PUBLIC_KEY=current_app.config["STRIPE_PUBLIC_KEY"])




#rotta crea prodotto
@main.route('/prodotti/nuovo', methods=['GET', 'POST'])
@login_required
@admin_required
def prodotto_create():
    form = ProdottoForm()

    # Popola le scelte del form
    form.categoria.choices = [(c.id, c.nome) for c in Categoria.query.all()]
    form.fornitori.choices = [(f.id, f.username) for f in User.query.filter_by(ruolo="FORNITORE")]

    if form.validate_on_submit():
        # Crea il prodotto
        prodotto = Prodotto(
            codice=form.codice.data,
            nome=form.nome.data,
            descrizione=form.descrizione.data,
            prezzo=form.prezzo.data,
            quantita=form.quantita.data,
            categoria_id=form.categoria.data,   # CORRETTO
            attivo=True
        )

        # Associa i fornitori selezionati
        fornitori_ids = form.fornitori.data
        prodotto.fornitori = [User.query.get(fid) for fid in fornitori_ids]

        # Salva nel DB
        db.session.add(prodotto)
        db.session.commit()

        flash('Prodotto creato con successo', 'success')
        return redirect(url_for('main.prodotti'))

    # GET → mostra il form
    return render_template('prodotti/form.html', form=form)

#MODIFICA LO STATO DELL'ORDINE
@main.route('/admin/ordine/<int:id>/stato', methods=['GET', 'POST'])
@login_required
@admin_required
def modifica_stato_ordine(id):
    ordine = Ordine.query.get_or_404(id)
    stati = ["PENDING", "CONFERMATO", "SPEDITO", "CONSEGNATO", "ANNULLATO"]

    if request.method == "POST":
        nuovo_stato = request.form.get("stato")
        if nuovo_stato in stati:
            vecchio_stato = ordine.stato
            ordine.stato = nuovo_stato
            db.session.commit()
            from app.email_notifiche import invia_notifica_ordine
            invia_notifica_ordine(ordine, vecchio_stato)
            flash("Stato aggiornato e mail inviata!", "success")
            page_corrente = request.form.get("page", 1)
            return redirect(url_for('main.gestione_ordini_admin', page=page_corrente))

    return render_template('ordini/modifica_stato.html', ordine=ordine, stati=stati)

#Sistema ordini, per la fase dell'ordinazione
@main.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = Cart()

    # Carrello vuoto
    if len(cart) == 0:
        flash("Carrello vuoto", "warning")
        return redirect(url_for('main.cart_view'))

    if request.method == "POST":
        errori = []

        # Controlli quantità e stock
        for item in cart:
            prodotto = Prodotto.query.get(item['prodotto_id'])
            if not prodotto:
                errori.append("Prodotto non trovato")
            elif not isinstance(item['qty'], int) or item['qty'] <= 0:
                errori.append(f"{prodotto.nome}: quantità non valida ({item['qty']})")
            elif item['qty'] > prodotto.quantita:
                errori.append(f"{prodotto.nome}: disponibili solo {prodotto.quantita}")

        if errori:
            for e in errori:
                flash(e, "danger")
            return redirect(url_for('main.cart_view'))

        try:
            # 🧾 CREA ORDINE
            ordine = Ordine(
                cliente_id=current_user.id,
                totale=cart.get_total(),
                email=current_user.email
            )

            db.session.add(ordine)
            db.session.flush()  # ottiene ordine.id

            # DETTAGLI ORDINE + SCALARE STOCK
            for item in cart:
                prodotto = Prodotto.query.get(item['prodotto_id'])

                dettaglio = OrdineDettaglio(
                    ordine_id=ordine.id,
                    prodotto_id=prodotto.id,
                    quantita=item['qty'],
                    prezzo_unitario=prodotto.prezzo
                )
                db.session.add(dettaglio)

                prodotto.quantita -= item['qty']

            db.session.commit()

            # Svuota carrello
            cart.clear()

            flash("Ordine creato! Procedi al pagamento.", "success")

            # 🔥 TORNA AL VECCHIO FLUSSO → pagina dettaglio ordine
            return redirect(url_for('main.dettaglio_ordine', id=ordine.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore checkout: {e}")
            flash("Errore durante il checkout. Riprova.", "danger")
            return redirect(url_for('main.cart_view'))

    # GET → mostra pagina riepilogo prima dell'ordine
    return render_template("carrello/checkout.html", cart=cart)




#route per le statistiche degli ordini
@main.route('/admin/statistiche-ordini')
@login_required
@admin_required
def statistiche_ordini():

    totale_ordini = Ordine.query.count()
    pending = Ordine.query.filter_by(stato="PENDING").count()
    confermato = Ordine.query.filter_by(stato="CONFERMATO").count()
    spedito = Ordine.query.filter_by(stato="SPEDITO").count()
    consegnato = Ordine.query.filter_by(stato="CONSEGNATO").count()

    totale_incassato = db.session.query(func.sum(Ordine.totale)).scalar() or 0

    return render_template(
        'ordini/statistiche_ordini.html',
        totale_ordini=totale_ordini,
        pending=pending,
        confermato=confermato,
        spedito=spedito,
        consegnato=consegnato,
        totale_incassato=totale_incassato
    )

#@main.route('/prodotti')
#def prodotto_list():
#    page = request.args.get('page', 1, type=int)
#    prodotti = Prodotto.query.filter_by(attivo=True).paginate(page=page, per_page=10)
#    return render_template('prodotti/list.html', prodotti=prodotti)



#route che porta a dettaglio prodotto 
@main.route('/prodotti/<int:id>')

def dettaglio_prodotto(id):
    prodotto = Prodotto.query.get_or_404(id)

#    if current_user.is_authenticated and current_user.ruolo == "FORNITORE":
#        if current_user not in prodotto.fornitori:
#            flash("Non hai accesso a questo prodotto")
#            return redirect(url_for('main.dashboard_fornitore'))

    return render_template('prodotti/dettaglio_prodotto.html', prodotto=prodotto)

#route per pagina modifica_fornitore, modifica i dati
@main.route('/fornitore/<int:id>/modifica', methods=['GET', 'POST'])
@roles_required("ADMIN", "FORNITORE")
def modifica_fornitore(id):
    origine = request.args.get('origine', request.form.get('origine', 'fornitori'))

    f = User.query.filter_by(id=id, ruolo="FORNITORE").first_or_404()

    prodotti = Prodotto.query.all()

    if request.method == 'POST':
        f.ragione_sociale = request.form['ragione_sociale']
        f.partita_iva = request.form['partita_iva']
        f.email = request.form['email']
        f.telefono = request.form['telefono']

        # aggiorna associazioni prodotti
        prodotti_ids = set(map(int, request.form.getlist('prodotti')))
        prodotti_attuali = set(p.id for p in f.prodotti)

        da_aggiungere = prodotti_ids - prodotti_attuali
        da_rimuovere = prodotti_attuali - prodotti_ids

        for pid in da_aggiungere:
            p = Prodotto.query.get(pid)
            f.prodotti.append(p)

        for pid in da_rimuovere:
            p = Prodotto.query.get(pid)
            f.prodotti.remove(p)

        db.session.commit()
        flash("Fornitore aggiornato con successo", "success")

        return redirect(url_for('main.dettaglio_fornitore', id=f.id, origine=origine))

    return render_template('fornitori/fornitore_modifica.html', f=f, prodotti=prodotti, origine=origine)


# ---------------------------------------------------------
# Home
# ---------------------------------------------------------
@main.route('/')
def home():
    

    categorie = Categoria.query.all()

    # Statistiche tramite funzione
    totale_categorie, categorie_attive, categorie_non_attive, percentuale_attive = get_statistiche()

    #recupera alcuni prodotti da mostrare
    prodotti_da_mostrare = Prodotto.query.filter_by(attivo=True).limit(5).all()

    nome_utente = "Visitatore"

    # Ultima categoria inserita
    ultima = Categoria.query.order_by(Categoria.id.desc()).first()

    return render_template(
        'layout/home.html',
        nome=nome_utente,
        categorie=categorie,
        totale_categorie=totale_categorie,
        categorie_attive=categorie_attive,
        categorie_non_attive=categorie_non_attive,
        percentuale_attive=percentuale_attive,
        ultima=ultima,
        prodotti_da_mostrare=prodotti_da_mostrare
    )
#prodotti nella dashboard_fornitore i suoi prodotti inseriti
@main.route('/fornitore/prodotti')
@fornitore_required
@login_required
def prodotti_fornitore():
    prodotti = current_user.prodotti
    return render_template('prodotti/prodotti_fornitore.html', prodotti=prodotti)

@main.route('/prodotti')

def prodotti():
    page = request.args.get('page', 1, type=int)
    categoria_id = request.args.get('categoria', type=int)
    search = request.args.get('q', '')

    query = Prodotto.query.filter_by(attivo=True)

    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)

    if search:
        query = query.filter(db.or_(
            Prodotto.nome.ilike(f"%{search}%"),
            Prodotto.codice.ilike(f"%{search}%")
        ))

    prodotti = query.all()
    categorie = Categoria.query.all()

    totale, attivi, non_attivi, valore_totale = get_statistiche_prodotti()

    return render_template(
        'prodotti/prodotti.html',
        prodotti=prodotti,
        categorie=categorie,
        totale=totale,
        attivi=attivi,
        non_attivi=non_attivi,
        valore_totale=valore_totale
    )

#modifica prodotto del fornitore
@main.route('/prodotti/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@admin_required
def prodotto_update(id):
    prodotto = Prodotto.query.get_or_404(id)

    # Precarico il form con i dati del prodotto
    form = ProdottoForm(obj=prodotto)

    # Popola le choices
    form.categoria.choices = [(c.id, c.nome) for c in Categoria.query.all()]
    form.fornitori.choices = [(f.id, f.username) for f in User.query.filter_by(ruolo="FORNITORE")]

    # Pre-seleziona i fornitori già associati
    form.fornitori.data = [f.id for f in prodotto.fornitori]

    if form.validate_on_submit():

        # Aggiorna manualmente i campi (senza populate_obj)
        prodotto.codice = form.codice.data
        prodotto.nome = form.nome.data
        prodotto.descrizione = form.descrizione.data
        prodotto.prezzo = form.prezzo.data
        prodotto.quantita = form.quantita.data
        prodotto.categoria_id = form.categoria.data

        # Aggiorna fornitori (relazione many-to-many)
        fornitori_ids = form.fornitori.data
        prodotto.fornitori = [User.query.get(fid) for fid in fornitori_ids]

        db.session.commit()
        flash('Prodotto aggiornato con successo', 'success')

        return redirect(url_for('main.dettaglio_prodotto', id=id))

    return render_template('prodotti/form.html', form=form, prodotto=prodotto)

#DETTAGLIO FORNITORE
@main.route('/fornitore/<int:id>')
@roles_required("ADMIN", "FORNITORE")
def dettaglio_fornitore(id):
    origine= request.args.get('origine', 'fornitori')
    f = User.query.filter_by(id=id, ruolo="FORNITORE").first_or_404(id)
    return render_template('fornitori/fornitore_dettaglio.html', f=f, origine=origine)

@main.route('/categorie')
def categorie():
    categorie = Categoria.query.all()
    return render_template('categorie/categorie_admin.html', categorie=categorie)

#rottaa eliminazione prodotto
@main.route('/prodotti/<int:id>/elimina', methods=['POST'])
@login_required
@admin_required
def prodotto_delete(id):
    prodotto = Prodotto.query.get_or_404(id)
    db.session.delete(prodotto)
    db.session.commit()
    flash('Prodotto eliminato con successo', 'success')
    return redirect(url_for('main.prodotti'))

#route modifica prodotto fornitore da lui inserito
@main.route('/fornitore/prodotti/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@fornitore_required
def modifica_prodotto_fornitore(id):
    # Recupera il prodotto
    prodotto = Prodotto.query.get_or_404(id)

    # Sicurezza: il prodotto deve appartenere al fornitore
    if current_user not in prodotto.fornitori:
        abort(403)

    # Precarica il form con i dati del prodotto
    form = ProdottoForm(obj=prodotto)

    # Popola le categorie
    form.categoria.choices = [(c.id, c.nome) for c in Categoria.query.all()]

    # Il fornitore può modificare solo se stesso come fornitore
    form.fornitori.choices = [(current_user.id, current_user.username)]
    form.fornitori.data = [current_user.id]

    if form.validate_on_submit():
        # Aggiorna i campi
        prodotto.nome = form.nome.data
        prodotto.descrizione = form.descrizione.data
        prodotto.prezzo = form.prezzo.data
        prodotto.quantita = form.quantita.data
        prodotto.categoria_id = form.categoria.data

        # Associa solo il fornitore corrente
        prodotto.fornitori = [current_user]

        # Salva
        db.session.commit()
        flash("Prodotto aggiornato con successo", "success")

        return redirect(url_for('main.prodotti_fornitore'))

    return render_template('prodotti/form.html', form=form, prodotto=prodotto)

#@main.route('/aggiungi-prodotto', methods=['GET', 'POST'])
#@roles_required("ADMIN", "FORNITORE")
#def aggiungi_prodotto():
#    categorie = Categoria.query.all()  # Per la select

#    if request.method == 'POST':
#        codice = request.form['codice']
#        nome = request.form['nome']
#        descrizione = request.form['descrizione']
#        prezzo = float(request.form['prezzo'])
#        quantita = int(request.form['quantita'])
#        attivo = 'attivo' in request.form
#        categoria_id = int(request.form['categoria_id'])

#        nuovo = Prodotto(
#            codice=codice,
#            nome=nome,
#            descrizione=descrizione,
#            prezzo=prezzo,
#            quantita=quantita,
#            attivo=attivo,
#            categoria_id=categoria_id
#        )
#        if current_user.ruolo == "FORNITORE":
#            nuovo.fornitori.append(current_user)

#        db.session.add(nuovo)
#        db.session.commit()

#        flash("Prodotto inserito con successo!", "success")
        
#        return redirect(url_for(
#            'main.prodotti_fornitore' if current_user.ruolo == "FORNITORE" else 'main.prodotti'
#        ))
#    return render_template('aggiungi_prodotto.html', categorie=categorie)


# ---------------------------------------------------------
# Rotta per aggiungere una categoria di test
# ---------------------------------------------------------
@main.route('/aggiungi-test')
@roles_required("ADMIN")
def aggiungi_test():
    nuova = Categoria(nome="Categoria di prova", descrizione="Inserita per test", attiva=True)
    db.session.add(nuova)
    db.session.commit()
    flash("Categoria inserita con successo!", "success")

    return "Categoria inserita!"

@main.route('/reset-test')
@roles_required("ADMIN")
def reset_test():
    # Cancella solo le categorie  
    Categoria.query.filter_by(nome="Categoria di prova").delete()
    db.session.commit()
    return "Categorie di prova eliminate!"

@main.route('/aggiungi-prodotto-test')
@roles_required("ADMIN")
def aggiungi_prodotto_test():
    # Crea una categoria di test
    cat = Categoria(nome="Elettronica", descrizione="Categoria test", attiva=True)
    db.session.add(cat)
    db.session.commit()

    # Crea un prodotto collegato alla categoria
    prod = Prodotto(
        codice="P002",
        nome="Mouse",
        descrizione="Mouse wireless",
        prezzo=29.99,
        quantita=10,
        attivo=True,
        categoria=cat
    )
    db.session.add(prod)
    db.session.commit()

    return "Prodotto inserito con successo!"



# ---------------------------------------------------------
# Dashboard per ruoli
# ---------------------------------------------------------

from flask_login import login_required, current_user
from app.utils.decorators import admin_required, fornitore_required, cliente_required
from sqlalchemy import func, desc
from app.models import User, Prodotto
#pagina dashboard_admin

@main.route('/dashboard_admin')
@login_required
@admin_required
def dashboard_admin():
    messaggi = Messaggio.query.order_by(Messaggio.data.desc()).all()
    # Totale utenti per ruolo
    utenti_per_ruolo = (
        db.session.query(
            User.ruolo,
            func.count(User.id).label('totale')
        )
        .group_by(User.ruolo)
        .all()
    )

    # Filtro categoria
    categoria_id = request.args.get('categoria', type=int)
    categorie = Categoria.query.all()

    # Se NON stai filtrando → mostra scorte basse
    if not categoria_id:
        scorte_basse = Prodotto.query.filter(
            Prodotto.quantita < 10,
            Prodotto.attivo == True
        ).all()
    else:
        scorte_basse = []  # evita duplicazioni

    # Prodotti filtrati per categoria
    if categoria_id:
        prodotti_filtrati = Prodotto.query.filter_by(categoria_id=categoria_id).all()
    else:
        prodotti_filtrati = Prodotto.query.all()

    # Ultimi 5 utenti registrati
    ultimi_utenti = (
        User.query
        .order_by(desc(User.id))
        .limit(5)
        .all()
    )

    # Statistiche prodotti
    stats = {
        'totale_prodotti': Prodotto.query.count(),
        'prodotti_attivi': Prodotto.query.filter_by(attivo=True).count()
    }

    # 📦 STATISTICHE ORDINI
    totale_ordini = Ordine.query.count()
    pending = Ordine.query.filter_by(stato="PENDING").count()
    confermato = Ordine.query.filter_by(stato="CONFERMATO").count()
    spedito = Ordine.query.filter_by(stato="SPEDITO").count()
    consegnato = Ordine.query.filter_by(stato="CONSEGNATO").count()

    totale_incassato = db.session.query(func.sum(Ordine.totale)).scalar() or 0

    return render_template(
        'dashboard/dashboard_admin.html',
        utenti_per_ruolo=utenti_per_ruolo,
        scorte_basse=scorte_basse,
        ultimi_utenti=ultimi_utenti,
        stats=stats,
        categorie=categorie,
        categoria_id=categoria_id,
        prodotti_filtrati=prodotti_filtrati,
        messaggi=messaggi,
        

        # 👉 PASSIAMO LE NUOVE STATISTICHE ALLA DASHBOARD
        totale_ordini=totale_ordini,
        pending=pending,
        confermato=confermato,
        spedito=spedito,
        consegnato=consegnato,
        totale_incassato=totale_incassato
    )

@main.route('/dashboard_fornitore')
@fornitore_required
@login_required
def dashboard_fornitore():
    prodotti = current_user.prodotti
    totale_prodotti = len(prodotti)
    totale_prezzi = sum(p.quantita for p in prodotti)
    return render_template('dashboard/dashboard_fornitore.html', prodotti=prodotti, totale_prodotti=totale_prodotti, totale_prezzi=totale_prezzi)

@main.route('/dashboard_cliente')
@login_required
@cliente_required
def dashboard_cliente():
    prodotti = Prodotto.query.filter_by(attivo=True).all()
    totale_ordini = Ordine.query.filter_by(cliente_id=current_user.id).count()
    pending_ordini = Ordine.query.filter_by(cliente_id=current_user.id, stato="PENDING").count()
    ultimi_pending = Ordine.query.filter_by(cliente_id=current_user.id, stato="PENDING") \
                                 .order_by(Ordine.data_ordine.desc()) \
                                 .limit(3).all()

    return render_template('dashboard/dashboard_cliente.html', prodotti=prodotti, totale_ordini=totale_ordini, pending_ordini=pending_ordini, ultimi_pending=ultimi_pending)




#ROUTE PER TESTARE PAGAMENTI SU STRIPE

@main.route('/test-stripe')
def test_stripe():
    try:
        intent = stripe.PaymentIntent.create(
            amount=1000,  # €10.00
            currency='eur'
        )
        return {'status': 'ok', 'client_secret': intent.client_secret}
    except stripe.error.StripeError as e:
        return {'error': str(e)}
    
#route pagamento
#@main.route('/create-payment-intent', methods=['POST'])
#def create_payment_intent():
#    data = request.get_json()

#    order_id = session.get("ordine_id")
#    ordine = Ordine.query.get(order_id)

#    if not ordine:
#        return jsonify({"error": "Ordine non trovato"}), 404

    # Salva i dati spedizione
#    ordine.nome = data.get("nome")
#    ordine.cognome = data.get("cognome")
#    ordine.indirizzo = data.get("indirizzo")
#    ordine.citta = data.get("citta")
#    ordine.cap = data.get("cap")
#    ordine.provincia = data.get("provincia")
#    ordine.telefono = data.get("telefono")
#    ordine.email = data.get("email")

    # Crea PaymentIntent
#    intent = stripe.PaymentIntent.create(
#        amount=data.get("amount"),
#        currency="eur",
#        automatic_payment_methods={"enabled": True}
#    )

#    ordine.payment_intent_id = intent.id
#    db.session.commit()

#    return jsonify({"clientSecret": intent.client_secret})
    

#@main.route('/checkout-payment/<int:order_id>')
#def checkout_payment(order_id):
#    ordine = Ordine.query.get_or_404(order_id)
#    session["ordine_id"] = ordine.id

#    return render_template(
#        "carrello/checkout_payment.html",
#        stripe_public_key=current_app.config["STRIPE_PUBLIC_KEY"],
#        amount=int(ordine.totale * 100)  # Stripe vuole i centesimi
#    )

#@main.route('/success')
#def success():
#    order_id = session.get("ordine_id")
#    if not order_id:
#        return "ordine non trovato", 404
#    ordine = Ordine.query.get(order_id)
#    if not ordine:
#        return "Ordine non trovato", 404
#    return render_template("carrello/success.html", ordine=ordine)

#crea pagamento stripe
@main.route('/pagamento/crea-sessione/<int:ordine_id>')
@login_required
def crea_sessione_stripe(ordine_id):
    import stripe
    from flask import current_app
    from flask_login import current_user

    ordine = Ordine.query.get_or_404(ordine_id)

    if ordine.stato == "CONFERMATO":
        flash("Questo ordine risulta gia pagato.", "info")
        return redirect(url_for('main.dettaglio_ordine', id=ordine.id))

    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

    # Sicurezza: solo il cliente può pagare il suo ordine
    if ordine.cliente.id != current_user.id:
        return redirect(url_for('main.home'))
    
    for det in ordine.dettagli:
        if det.quantita > det.prodotto.quantita:
            flash(f"Il prodotto {det.prodotto.nome} non è piu disponibile in quantita sufficiente.", "danger")
            return redirect(url_for('main.dettaglio_ordine', id=ordine.id))
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

    # Line items per Stripe (DEVE essere prima del print)
    line_items = []
    for det in ordine.dettagli:
        
        line_items.append({
            'price_data': {
                'currency': 'eur',
                'product_data': {
                    'name': det.prodotto.nome,

                },
                'unit_amount': int(det.prezzo_unitario * 100),
            },
            'quantity': det.quantita,
        })

    

    # CREA LA SESSIONE STRIPE
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=url_for('main.pagamento_success', ordine_id=ordine.id, _external=True),
        cancel_url=url_for('main.pagamento_cancel', ordine_id=ordine.id, _external=True),
        metadata={'ordine_id': ordine.id}
    )

    # SALVA session.id NELL’ORDINE
    ordine.stripe_session_id = session.id
    db.session.commit()

    # REDIRECT AL CHECKOUT
    return redirect(session.url)

@main.route('/pagamento/success/<int:ordine_id>')
@login_required
def pagamento_success(ordine_id):
    ordine = Ordine.query.get_or_404(ordine_id)
    ordine.stato = 'CONFERMATO'
    db.session.commit()
    return render_template('carrello/success.html', ordine=ordine)
#gestire pagamento in caso di annulla
@main.route('/pagamento/cancel/<int:ordine_id>')
@login_required
def pagamento_cancel(ordine_id):
    ordine = Ordine.query.get_or_404(ordine_id)
    return render_template("carrello/cancel.html", ordine=ordine)

#ROUTE PAGAMENTO STRIPE
#@main.route('/prepare_checkout_stripe/<int:ordine_id>', methods=['POST'])
#def prepare_checkout_stripe(ordine_id):
#    import stripe
#    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
#    ordine = Ordine.query.get_or_404(ordine_id)
#    if ordine.cliente_id != current_user.id:
#        flash("non puoi pagare un ordine non tuo", "danger")
#        return redirect(url_for('main.home'))
#    # 1. CREA CUSTOMER STRIPE SE NON ESISTE
#    if current_user.stripe_customer_id is None:
#        customer = stripe.Customer.create(
#            email=current_user.email,
            
#        )
#        current_user.stripe_customer_id = customer.id
#        db.session.commit() 
            # 2. CREA SESSIONE CHECKOUT LEGATA AL CUSTOMER
#    session = stripe.checkout.Session.create(
#        payment_method_types=['card'],
#        mode='payment',
#        customer=current_user.stripe_customer_id,
#        line_items=[
#            {
#                'price_data': {
#                    'currency': 'eur',
#                    'product_data': {
#                        'name': f"Ordine #{ordine.id}",

#                    },
#                    'unit_amount': int(ordine.totale * 100),
#                },
#                'quantity': 1,
#            }
#        ],
#        metadata={
#            'ordine_id': ordine.id,
#            'utente_id': current_user.id
#        },
        
#        success_url=url_for('main.pagamento_success', ordine_id=ordine.id, _external=True),
#        cancel_url=url_for('main.pagamento_cancel', ordine_id=ordine.id, _external=True)
#    )
#    return redirect(session.url, code=303)

  

#route stripe
#@main.route('/webhook', methods=['POST'])

#def stripe_webhook():
#    print("WEBHOOK CHIAMATO")
#    payload = request.get_data()
#    sig = request.headers.get('Stripe-Signature')

#    try:
#        event = stripe.Webhook.construct_event(
#           payload, sig, current_app.config['STRIPE_WEBHOOK_SECRET']
#        )
#    except Exception as e:
#        print("Errore firma webhook:", e)
#        return 'Error', 400

#    if event['type'] == 'checkout.session.completed':
#        session = event['data']['object']
#       ordine_id = session['metadata'].get('ordine_id')

#        if ordine_id:
#            ordine = Ordine.query.get(int(ordine_id))
#            if ordine and ordine.stato == 'PENDING':
#                ordine.pagato = True
#                ordine.stato = 'CONFERMATO'
#               db.session.commit()
#                print(f"Ordine {ordine.id} confermato via webhook")
#    print("Evento ricevuto:", event['type'])

#    return 'OK', 200


#ROUTE PER CSV


@main.route('/admin/ordini/export')
@admin_required
def export_ordini():
    output = StringIO()
    writer = csv.writer(output)
    
    # intestazioni CSV
    writer.writerow(['ID Ordine', 'Cliente', 'Email', 'Data Ordine', 'Stato', 'Totale'])

    # ordini ordinati per data decrescente
    ordini = Ordine.query.order_by(Ordine.data_ordine.desc()).all()

    for ordine in ordini:
        writer.writerow([
            ordine.id,
            ordine.cliente.username,
            ordine.cliente.email,
            ordine.data_ordine.strftime('%d/%m/%Y'),
            ordine.stato,
            f"{ordine.totale:.2f}".replace('.', ',')  # formato italiano
        ])

    output.seek(0)
    return Response(
        output.getvalue().encode('utf-8'),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=ordini.csv'}
    )

#ROUTE PER ELIMINARE CATEGORIA

@main.route('/elimina_categoria/<int:id>', methods=['POST'])
@login_required  # Assicurati che solo l'admin possa farlo
def elimina_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    
    # Opzionale: Controlla se ci sono prodotti associati
    prodotti_collegati = Prodotto.query.filter_by(categoria_id=id).first()
    if prodotti_collegati:
        # Messaggio di errore se la categoria non è vuota
        flash("Impossibile eliminare: sposta prima i prodotti in un'altra categoria!", "danger")
        return redirect(url_for('main.dashboard_admin'))

    db.session.delete(categoria)
    db.session.commit()
    flash(f"Categoria '{categoria.nome}' eliminata con successo!", "success")
    return redirect(url_for('main.dashboard_admin'))
#GESTIRE LE CATEGORIE
@main.route('/admin/categorie')
@login_required
def gestione_categorie():
    categorie = Categoria.query.all()
    return render_template('categorie/admin_categorie.html', categorie=categorie)


#CATEGORIA ADMIN
@main.route('/categorie/nuova', methods=['GET', 'POST'])
def nuova_categoria():
    form = CategoriaForm()

    if form.validate_on_submit():
        nuova = Categoria(nome=form.nome.data)
        db.session.add(nuova)
        db.session.commit()
        flash("Categoria aggiunta con successo", "success")
        return redirect(url_for('main.categorie'))

    return render_template('categorie/categorie_admin.html', form=form)

#ROUTE PER INSERIRE DATI DELLA SPEDIZIONE
@main.route('/ordine/<int:ordine_id>/spedizione', methods=['GET', 'POST'])
@login_required
def dati_spedizione(ordine_id):
    ordine = Ordine.query.get_or_404(ordine_id)

    # Sicurezza: solo il proprietario può modificare i suoi dati
    if ordine.cliente.id != current_user.id:
        return redirect(url_for('main.home'))
    
    form = SpedizioneForm()

    if request.method == 'POST':
        ordine.nome_spedizione = request.form['nome']
        ordine.cognome_spedizione = request.form['cognome']
        ordine.indirizzo = request.form['indirizzo']
        ordine.citta = request.form['citta']
        ordine.cap = request.form['cap']
        ordine.telefono = request.form['telefono']
        ordine.note_spedizione = request.form.get('note', '')

        db.session.commit()

        # Dopo aver salvato → vai a Stripe
        return redirect(url_for('main.crea_sessione_stripe', ordine_id=ordine.id))

    return render_template('ordini/spedizione.html', form=form, ordine=ordine)


#@main.route("/verify/<token>")
#def conferma_email(token):
#    try:
#        email = verifica_token(token)
#    except:
#        return "Link non valido o scaduto"
#    user = User.query.filter_by(email=email).first_or_404()
#    user.email_verificata = True
#    db.session.commit()
#    flash("Email confermata| ora puoi accedere")
#    return redirect(url_for('auth.login'))


@main.route("/privacy")
def privacy():
    return render_template("condizioni/privacy.html")

@main.route("/termini")
def termini():
    return render_template("condizioni/termini.html")

@main.route("/contatti", methods=["POST", "GET"])
def contatti():
    form = ContattiForm()
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        messaggio = request.form.get("messaggio")
        msg = Messaggio(nome=nome, email=email, messaggio=messaggio)
        db.session.add(msg)
        db.session.commit()
        flash("Messaggio inviato correttamente!", "success")
        return redirect(url_for("main.contatti"))
    return render_template("condizioni/contatti.html", form=form)


@main.route("/messaggi_admin")
@login_required
@admin_required
def messaggi_admin():
    messaggi = Messaggio.query.order_by(Messaggio.data.desc()).all()
    return render_template("dashboard/messaggi_admin.html", messaggi=messaggi)

@main.route("/messaggi_admin/rispondi/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def rispondi_messaggio(id):
    msg = Messaggio.query.get_or_404(id)
    form = RispostaForm()

    if request.method == "POST":
        risposta = request.form.get("risposta")

        send_email(
            to=msg.email,
            subject="Risposta alla tua richiesta",
            body=f"Ciao {msg.nome}, \n\n{risposta}\n\nCordiali saluti."
        )

      

        flash("Risposta inviata con successo!", "success")
        return redirect(url_for("main.messaggi_admin"))

    return render_template("dashboard/rispondi_messaggio.html", msg=msg, form=form)

#ROUTE PER IMPOSTAZIONI GENERALI CHE SMISTA IN BASE AL RUOLO
@main.route("/impostazioni", methods=["GET"])
@login_required
def impostazioni():
    if current_user.ruolo == "FORNITORE":
        return redirect(url_for("main.impostazioni_fornitore"))
    else:
        return redirect(url_for("main.impostazioni_cliente"))

######## ROUTE PER IMPOSTAZIONE CLIENTE

@main.route("/impostazioni", methods=["GET"])
@login_required
def impostazioni_cliente():
    form_personali = DatiPersonaliForm(obj=current_user)
    form_indirizzi = IndirizziForm(obj=current_user)
    form_password = PasswordForm()
    form_preferenze = PreferenzeForm(obj=current_user)

    return render_template(
        "impostazioni/impostazioni_cliente.html",
        form_personali=form_personali,
        form_indirizzi=form_indirizzi,
        form_password=form_password,
        form_preferenze=form_preferenze
    )

@main.route("/salva_dati_personali", methods=["POST"])
@login_required
def salva_dati_personali():
    form = DatiPersonaliForm(request.form)

    if form.validate_on_submit():
        current_user.nome = form.nome.data
        current_user.cognome = form.cognome.data
        current_user.telefono = form.telefono.data
        db.session.commit()
        flash("Dati salvati", "success")
    else:
        print("Form non valido:", form.errors)

    return redirect(url_for('main.impostazioni_cliente'))


@main.route("/cambia_password", methods=["POST"])
@login_required
def cambia_password():
    form = PasswordForm(request.form)

    if form.validate_on_submit():
        if not current_user.check_password(form.password_attuale.data):
            flash("La password attuale non è corretta", "danger")
            return redirect(url_for('main.impostazioni_cliente'))

        current_user.set_password(form.nuova_password.data)
        db.session.commit()
        flash("Password aggiornata correttamente", "success")

    return redirect(url_for('main.impostazioni_cliente'))


@main.route("/salva_preferenze", methods=["POST"])
@login_required
def salva_preferenze():
    form = PreferenzeForm(request.form)

    if form.validate_on_submit():
        current_user.notifiche_ordini = form.notifiche_ordini.data
        current_user.newsletter = form.newsletter.data
        current_user.promozioni = form.promozioni.data
        db.session.commit()
        flash("Preferenze aggiornate correttamente", "success")

    return redirect(url_for('main.impostazioni_cliente'))


@main.route("/salva_indirizzi", methods=["POST"])
@login_required
def salva_indirizzi():
    form = IndirizziForm()

    if form.validate_on_submit():
        current_user.indirizzo_spedizione = form.indirizzo_spedizione.data
        current_user.indirizzo_fatturazione = form.indirizzo_fatturazione.data
        db.session.commit()
        flash("Indirizzi aggiornati correttamente", "success")
    else:
        print("Form indirizzi non valido:", form.errors)

    return redirect(url_for('main.impostazioni_cliente'))

##### FINE RUOTE IMPOSTAZIONE CLIENTE

#### RUOTE IMPOSTAZIONE FORNITORE
@main.route("/impostazioni_fornitore", methods=["GET"])
@login_required
def impostazioni_fornitore():
    if current_user.ruolo != "FORNITORE":
        return redirect(url_for("main.impostazioni_cliente"))

    form_password = PasswordForm()
    return render_template(
        "impostazioni/impostazioni_fornitore.html",
        form_password=form_password
    )


@main.route("/disattiva_account", methods=["POST"])
@login_required
def disattiva_account():
    # Solo fornitori possono disattivare da questa pagina
    if current_user.ruolo != "FORNITORE":
        flash("Non hai i permessi per disattivare questo account.", "danger")
        return redirect(url_for("main.impostazioni_cliente"))

    user_id = current_user.id

    # Logout prima di eliminare
    logout_user()

    # Recupera l'utente dal DB e lo elimina
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash("Il tuo account è stato disattivato ed eliminato definitivamente.", "success")
    else:
        flash("Errore: account non trovato.", "danger")

    return redirect(url_for("main.index"))