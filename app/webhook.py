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
    import stripe
    
    

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
        current_app.logger.info(f"Ordine pagato: {ordine.id}")


        ordine = Ordine.query.filter_by(stripe_session_id=session_id).first()

        if ordine:
            ordine.pagato = True
            db.session.commit()
            

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
            try:
                sg = SendGridAPIClient(current_app.config['SENDGRID_API_KEY'])
                response = sg.send(message)
            except Exception as e:
                current_app.logger.error(f"Errore invio email: {e}")

        else:
            current_app.logger.warning("Ordine non trovato per session ID")

    
    return jsonify({'status': 'success'}), 200

            

# route fattura pdf
def genera_fattura_pdf(ordine):
    
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    larghezza, altezza = A4
    y = altezza - 50

    # 🔵 HEADER COLORATO
    pdf.setFillColorRGB(0.12, 0.47, 0.95)  # blu elegante
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

    # Header tabella
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

    # 🔹 TOTALE EVIDENZIATO
    pdf.setFillColorRGB(0.95, 0.95, 0.95)
    pdf.rect(300, y - 30, 200, 30, fill=1, stroke=0)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(310, y - 10, f"Totale: € {ordine.totale:.2f}")

    pdf.save()
    buffer.seek(0)
    return buffer