from flask_mail import Message
from app import mail

def invia_email_conferma_pagamento(ordine, pdf_buffer):
    msg = Message(
        subject=f"Conferma pagamento ordine #{ordine.id}",
        recipients=[ordine.email]
    )

    msg.body = (
        f"Ciao {ordine.nome},\n\n"
        f"Abbiamo ricevuto il pagamento del tuo ordine #{ordine.id}.\n"
        f"Totale: € {ordine.totale}\n\n"
        "In allegato trovi la fattura in PDF.\n\n"
        "Grazie per aver acquistato da noi!"
    )

    msg.attach(
        f"Fattura_{ordine.id}.pdf",
        "application/pdf",
        pdf_buffer.read()
    )

    mail.send(msg)