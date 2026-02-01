import os
import json
import base64
import requests
from dotenv import load_dotenv
from flask import url_for
from app.utils.token import genera_token
import certifi

load_dotenv()

def send_email(to, subject, body, pdf_buffer=None, pdf_filename="ordine.pdf"):
    url = "https://api.sendgrid.com/v3/mail/send"

    headers = {
        "Authorization": f"Bearer {os.getenv('SENDGRID_API_KEY')}",
        "Content-Type": "application/json"
    }

    # Corpo email migliorato
    testo_plain = f"""Gentile cliente,

Abbiamo ricevuto il tuo messaggio tramite il sito e ti rispondiamo con piacere.

{body}

Grazie per averci contattato.
Cordiali saluti,
Il team di Supporto
"""

    html = f"""
    <h3>Gentile cliente,</h3>
    <p>Abbiamo ricevuto il tuo messaggio tramite il sito e ti rispondiamo con piacere.</p>
    <div style="margin-top: 20px; padding: 10px; background-color: #f4f4f4; border-left: 4px solid #007bff;">
        {body}
    </div>
    <p style="margin-top: 30px;">Grazie per averci contattato.<br>
    Cordiali saluti,<br>
    <strong>Il team di Supporto</strong></p>
    """

    data = {
        "personalizations": [{
            "to": [{"email": to}],
            "subject": subject
        }],
        "from": {"email": os.getenv("SENDGRID_SENDER")},
        "content": [
            {"type": "text/plain", "value": testo_plain},
            {"type": "text/html", "value": html}
        ]
    }

    # Se c'è un PDF, lo allego
    if pdf_buffer:
        encoded_pdf = base64.b64encode(pdf_buffer.read()).decode()
        data["attachments"] = [{
            "content": encoded_pdf,
            "type": "application/pdf",
            "filename": pdf_filename,
            "disposition": "attachment"
        }]

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), verify=certifi.where())
        print(f"Status: {response.status_code}")
        print(response.text)
    except Exception as e:
        print(f"Errore invio email: {e}")


def invia_email_verifica(user):
    token = genera_token(user.email)
    link = url_for('auth.verify_email', token=token, _external=True)

    subject = "Conferma la tua registrazione"
    recipient = user.email

    testo_plain = f"Conferma la tua email cliccando qui: {link}"
    html = f"""
    <h2>Benvenuto {user.username}!</h2>
    <p>Per completare la registrazione, conferma la tua email cliccando il link qui sotto:</p>
    <p><a href="{link}">Conferma email</a></p>
    """

    data = {
        "personalizations": [{
            "to": [{"email": recipient}],
            "subject": subject
        }],
        "from": {"email": os.getenv("SENDGRID_SENDER")},
        "content": [
            {"type": "text/plain", "value": testo_plain},
            {"type": "text/html", "value": html}
        ]
    }

    headers = {
        "Authorization": f"Bearer {os.getenv('SENDGRID_API_KEY')}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers=headers,
        data=json.dumps(data),
        verify=certifi.where()
    )
    print("EMAIL VERIFICA STATUS:", response.status_code)
    print(response.text)