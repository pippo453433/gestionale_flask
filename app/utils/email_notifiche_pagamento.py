from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64
import os

def invia_email_conferma_pagamento(ordine, pdf_buffer):
    subject = f"Conferma pagamento ordine #{ordine.id}"
    recipient = ordine.email
    mittente = "testdev99661@gmail.com"  # usa il tuo mittente verificato

    # Corpo testo
    testo_plain = (
        f"Ciao {ordine.nome},\n\n"
        f"Abbiamo ricevuto il pagamento del tuo ordine #{ordine.id}.\n"
        f"Totale: € {ordine.totale}\n\n"
        "In allegato trovi la fattura in PDF.\n\n"
        "Grazie per aver acquistato da noi!"
    )

    # Codifica PDF in base64
    pdf_base64 = base64.b64encode(pdf_buffer.read()).decode()

    attachment = Attachment()
    attachment.file_content = FileContent(pdf_base64)
    attachment.file_type = FileType("application/pdf")
    attachment.file_name = FileName(f"Fattura_{ordine.id}.pdf")
    attachment.disposition = Disposition("attachment")

    # Email SendGrid
    message = Mail(
        from_email=mittente,
        to_emails=recipient,
        subject=subject,
        plain_text_content=testo_plain
    )
    message.attachment = attachment

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"[EMAIL] Fattura PDF inviata a {recipient}")
        print("SENDGRID STATUS:", response.status_code)
    except Exception as e:
        print(f"[ERRORE EMAIL] {e}")