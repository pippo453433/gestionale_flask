import stripe
import json
from app import mail
from flask import Blueprint, request, jsonify, current_app
from app.models import db, Ordine
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from flask_mail import Message

webhook_bp = Blueprint('webhook_bp', __name__)

@webhook_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    print("WEBHOOK LOADED")
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config['STRIPE_WEBHOOK_SECRET']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception:
        return jsonify({'error': 'Invalid payload'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session['id']

        print("SESSION ID RICEVUTO:", session_id)

        ordine = Ordine.query.filter_by(stripe_session_id=session_id).first()

        if ordine:
            ordine.pagato = True
            db.session.commit()
            print("ORDINE PAGATO:", ordine.id)

            # 🔥 GENERA PDF
            pdf_buffer = genera_fattura_pdf(ordine)

            # 🔥 CREA EMAIL
            msg = Message(
                subject=f"Conferma pagamento ordine #{ordine.id}",
                recipients=[ordine.email],
                sender=current_app.config['MAIL_USERNAME']
            )

            msg.body = (
                f"Ciao {ordine.nome},\n\n"
                f"Il tuo ordine #{ordine.id} è stato pagato con successo.\n"
                f"In allegato trovi la fattura in PDF.\n\n"
                f"Grazie per il tuo acquisto!"
            )

            # 🔥 ALLEGA PDF
            msg.attach(
                f"fattura_{ordine.id}.pdf",
                "application/pdf",
                pdf_buffer.read()
            )

            # 🔥 INVIA EMAIL
            with current_app.app_context():
                mail.send(msg)

            print("EMAIL INVIATA PER ORDINE:", ordine.id)

        else:
            print("ORDINE NON TROVATO PER SESSION ID")

    return jsonify({'status': 'success'}), 200


# route fattura pdf
def genera_fattura_pdf(ordine):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    larghezza, altezza = A4
    y = altezza - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, f"Fattura Ordine #{ordine.id}")
    y -= 30

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y, f"Cliente: {ordine.nome} {ordine.cognome}")
    y -= 20
    pdf.drawString(50, y, f"Email: {ordine.email}")
    y -= 20
    pdf.drawString(50, y, f"Data ordine: {ordine.data_ordine.strftime('%d/%m/%Y')}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Dettagli ordine:")
    y -= 20

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, "Prodotto")
    pdf.drawString(250, y, "Quantità")
    pdf.drawString(330, y, "Prezzo")
    pdf.drawString(400, y, "Subtotale")
    y -= 15
    pdf.line(50, y, 550, y)
    y -= 20

    pdf.setFont("Helvetica", 11)

    for det in ordine.dettagli:
        pdf.drawString(50, y, det.prodotto.nome)
        pdf.drawString(250, y, str(det.quantita))
        pdf.drawString(330, y, f"€ {det.prezzo_unitario}")
        pdf.drawString(400, y, f"€ {det.subtotale}")
        y -= 20

        if y < 80:
            pdf.showPage()
            y = altezza - 50

    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, f"Totale ordine: € {ordine.totale}")

    pdf.save()
    buffer.seek(0)
    return buffer