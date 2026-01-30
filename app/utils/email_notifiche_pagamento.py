import os
import json
import base64
import requests
import certifi

def invia_email_conferma_pagamento(ordine, pdf_buffer):
    print(f"📤 Invio email a {ordine.email}")
    print(f"📎 PDF size: {pdf_buffer.getbuffer().nbytes} bytes")

    subject = f"Conferma pagamento ordine #{ordine.id}"
    recipient = ordine.email
    mittente = "testdev12311@outlook.com"  # mittente verificato

    # Corpo testo (fallback)
    testo_plain = (
        f"Ciao {ordine.nome},\n\n"
        f"Abbiamo ricevuto il pagamento del tuo ordine #{ordine.id}.\n"
        f"Totale: € {ordine.totale}\n\n"
        "In allegato trovi la fattura in PDF.\n\n"
        "Grazie per aver acquistato da noi!"
    )

    # HTML elegante (non modificato)
    html_template = f"""<!DOCTYPE html>
    <html lang="it">
    <head>
      <meta charset="UTF-8">
      <title>Conferma pagamento ordine #{ordine.id}</title>
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
      <div style="max-width: 600px; margin: auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);">

        <h2 style="color: #1e88e5; margin-top: 0;">
          Pagamento confermato – Ordine #{ordine.id}
        </h2>

        <p style="font-size: 15px; color: #444;">
          Ciao <strong>{ordine.nome}</strong>,
        </p>

        <p style="font-size: 15px; color: #444;">
          abbiamo ricevuto correttamente il pagamento del tuo ordine.
        </p>

        <p style="font-size: 15px; color: #444;">
          <strong>Totale pagato:</strong> € {ordine.totale}
        </p>

        <p style="font-size: 15px; color: #444;">
          In allegato trovi la tua fattura in formato PDF.
        </p>

        <div style="margin-top: 30px; padding: 15px; background-color: #e3f2fd; border-left: 4px solid #1e88e5; border-radius: 4px;">
          <p style="margin: 0; font-size: 14px; color: #1e88e5;">
            Grazie per aver acquistato da noi!  
          </p>
        </div>

        <p style="font-size: 12px; color: #999; margin-top: 40px; text-align: center;">
          Questo è un messaggio automatico · Non rispondere a questa email
        </p>

      </div>
    </body>
    </html>"""

    # Codifica PDF in base64
    pdf_buffer.seek(0)
    pdf_base64 = base64.b64encode(pdf_buffer.read()).decode()

    # Costruzione payload SendGrid
    data = {
        "personalizations": [{
            "to": [{"email": recipient}],
            "subject": subject
        }],
        "from": {"email": mittente},
        "content": [
            {"type": "text/plain", "value": testo_plain},
            {"type": "text/html", "value": html_template}
        ],
        "attachments": [{
            "content": pdf_base64,
            "type": "application/pdf",
            "filename": f"Fattura_{ordine.id}.pdf",
            "disposition": "attachment"
        }]
    }

    headers = {
        "Authorization": f"Bearer {os.getenv('SENDGRID_API_KEY')}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers=headers,
            data=json.dumps(data),
            verify=certifi.where()
        )
        
        print(response.text)
    except Exception as e:
        print(f"[ERRORE EMAIL] {e}")