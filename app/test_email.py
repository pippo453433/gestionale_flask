import os
import sys

# Aggiunge la root del progetto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.email_utils import send_email

# Cambia questo con la tua email per test
destinatario = "testdev12311@outlook.com"

send_email(
    to=destinatario,
    subject="Test invio email dal gestionale",
    body="Se ricevi questa email, SendGrid funziona!"
)