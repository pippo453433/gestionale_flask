import stripe
import json
from flask import Blueprint, request, jsonify, current_app
from app.models import db, Ordine
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO

# SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

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

            # 🔥 HTML elegante
            html_content = f"""
            <!DOCTYPE html>
            <html>
              <head>
                <meta charset="UTF-8">
                <style>
                  body {{
                    font-family: Arial, sans-serif;
                    background-color: #f9f9f9;
                    padding: 20px;
                    color: #333;
                  }}
                  .container {{
                    background-color: #fff;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                  }}
                  h2 {{
                    color: #007BFF;
                  }}
                  .footer {{
                    margin-top: 30px;
                    font-size: 12px;
                    color: #888;
                  }}
                </style>
              </head>
              <body>
                <div class="container">
                  <h2>Conferma pagamento ordine #{ordine.id}</h2>
                  <p>Ciao {ordine.nome},</p>
                  <p>Il tuo ordine <strong>#{ordine.id}</strong> è stato pagato con successo.</p>
                  <p>In allegato trovi la fattura in PDF.</p>
                  <p>Grazie per il tuo acquisto!</p>
                  <div class="footer">
                    Questa email è generata automaticamente dal sistema gestionale.
                  </div>
                </div>
              </body>
            </html>
            """

            # 🔥 CREA EMAIL SENDGRID
            message = Mail(
                from_email='testdev99661@gmail.com',
                to_emails=ordine.email,
                subject=f"Conferma pagamento ordine #{ordine.id}",
                html_content=html_content
            )

            # 🔥 ALLEGA PDF
            encoded_pdf = base64.b64encode(pdf_buffer.read()).decode()
            attachment = Attachment(
                FileContent(encoded_pdf),
                FileName(f"fattura_{ordine.id}.pdf"),
                FileType("application/pdf"),
                Disposition("attachment")
            )
            message.attachment = attachment

            # 🔥 INVIA EMAIL
            sg = SendGridAPIClient(current_app.config['SENDGRID_API_KEY'])
            sg.send(message)

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