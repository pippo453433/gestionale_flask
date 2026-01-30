import stripe
import json
from flask import Blueprint, request, jsonify, current_app
from app.models import db, Ordine
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from app.utils.email_notifiche_pagamento import invia_email_conferma_pagamento

# SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64
from app.email_utils import send_email 


webhook_bp = Blueprint('webhook_bp', __name__)

@webhook_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    

    import stripe

    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    endpoint_secret = current_app.config['STRIPE_WEBHOOK_SECRET']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        print("❌ ERRORE VERIFICA FIRMA:", e)
        return jsonify({'error': 'Invalid payload'}), 400

    current_app.logger.info(f"SendGrid key loaded: {bool(current_app.config['SENDGRID_API_KEY'])}")

    if event['type'] == 'checkout.session.completed':
        try:
            session = event['data']['object']
            session_id = session['id']
            payment_intent = session.get('payment_intent')

            ordine = Ordine.query.filter_by(stripe_session_id=session_id).first()
            if not ordine:
                current_app.logger.warning(f"Nessun ordine trovato per session_id {session_id}")
                return jsonify({'status': 'ok'}), 200

            ordine.pagato = True
            ordine.stato = "CONFERMATO"
            ordine.stripe_payment_intent = payment_intent
            db.session.commit()

            pdf_buffer = genera_fattura_pdf(ordine)
            invia_email_conferma_pagamento(ordine, pdf_buffer)

        except Exception as e:
            current_app.logger.error(f"Errore nel webhook: {e}")
            return jsonify({'status': 'errore'}), 500

    return jsonify({'status': 'success'}), 200

        


# route fattura pdf
def genera_fattura_pdf(ordine):

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    larghezza, altezza = A4
    y = altezza - 50

    # 🔵 HEADER COLORATO
    pdf.setFillColorRGB(0.12, 0.47, 0.95)
    pdf.rect(0, y - 40, larghezza, 60, fill=1, stroke=0)

    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(40, y, f"Fattura Ordine #{ordine.id}")

    y -= 80

    # 🔹 BOX DATI CLIENTE
    pdf.setFillColorRGB(0.95, 0.95, 0.95)
    pdf.rect(30, y - 70, larghezza - 60, 70, fill=1, stroke=0)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y - 20, "Dati Cliente:")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, y - 40, f"Nome: {ordine.nome} {ordine.cognome}")
    pdf.drawString(40, y - 55, f"Email: {ordine.email}")
    pdf.drawString(40, y - 70, f"Data ordine: {ordine.data_ordine.strftime('%d/%m/%Y')}")

    y -= 120

    # 🔹 TABELLA PRODOTTI
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Dettagli ordine:")
    y -= 25

    pdf.setFillColorRGB(0.88, 0.95, 1)
    pdf.rect(30, y - 20, larghezza - 60, 25, fill=1, stroke=0)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y - 5, "Prodotto")
    pdf.drawString(240, y - 5, "Quantità")
    pdf.drawString(330, y - 5, "Prezzo")
    pdf.drawString(420, y - 5, "Subtotale")

    y -= 35

    pdf.setFont("Helvetica", 11)

    for det in ordine.dettagli:
        pdf.drawString(40, y, det.prodotto.nome)
        pdf.drawString(240, y, str(det.quantita))
        pdf.drawString(330, y, f"€ {det.prezzo_unitario:.2f}")
        pdf.drawString(420, y, f"€ {det.subtotale:.2f}")
        y -= 20

        if y < 100:
            pdf.showPage()
            y = altezza - 50

    pdf.setFillColorRGB(0.95, 0.95, 0.95)
    pdf.rect(300, y - 30, 200, 30, fill=1, stroke=0)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(310, y - 10, f"Totale: € {ordine.totale:.2f}")

    pdf.save()
    buffer.seek(0)
    return buffer


@webhook_bp.route('/webhook-test', methods=['GET'])
def webhook_test():
    print("WEBHOOK TEST CHIAMATO")
    return "OK TEST WEBHOOK", 200