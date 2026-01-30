from flask import url_for
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
import requests
import certifi
import json

def invia_notifica_ordine(ordine, vecchio_stato, app=None):
    """
    Invia una email al cliente quando lo stato dell'ordine cambia (testo + HTML).
    """

    if app is None:
        from flask import current_app
        app = current_app

    subject = f"Aggiornamento ordine #{ordine.id}"
    recipient = ordine.cliente.email

    # VERSIONE TESTO (fallback)
    testo_plain = f"""
Ciao {ordine.cliente.username},

lo stato del tuo ordine #{ordine.id} è stato aggiornato.

Stato precedente: {vecchio_stato}
Nuovo stato: {ordine.stato}

Grazie per aver acquistato da noi!
"""

    # Link ordine
    with app.app_context():
        try:
            link_ordine = url_for('main.dettaglio_ordine', id=ordine.id, _external=True)
        except Exception:
            link_ordine = None

    # 🎨 Badge dinamico
    colori_stato = {
        "PENDING":    ("#fff8e1", "#fbc02d"),
        "CONFERMATO": ("#e3f2fd", "#1e88e5"),
        "SPEDITO":    ("#ffe0b2", "#fb8c00"),
        "CONSEGNATO": ("#e8f5e9", "#43a047"),
        "ANNULLATO":  ("#ffebee", "#e53935")
    }

    bg, fg = colori_stato.get(ordine.stato.upper(), ("#eeeeee", "#555"))

    # 🧠 Testo dinamico
    testo_stato = {
        "PENDING":    "Il tuo ordine è in attesa di conferma.",
        "CONFERMATO": "Il tuo ordine è stato confermato e verrà preparato a breve.",
        "SPEDITO":    "Il tuo ordine è in viaggio 🚚",
        "CONSEGNATO": "Il tuo ordine è stato consegnato. Speriamo ti piaccia!",
        "ANNULLATO":  "Il tuo ordine è stato annullato. Contattaci se hai bisogno di assistenza."
    }

    testo_dinamico = testo_stato.get(ordine.stato.upper(), "")
    ora_aggiornamento = datetime.now().strftime("%d/%m/%Y %H:%M")

    # HTML MIGLIORATO
    html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>{subject}</title>
</head>
<body style="margin:0; padding:0; background-color:#f4f4f4; font-family: Arial, Helvetica, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f4; padding:20px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
          
          <!-- HEADER -->
          <tr>
            <td style="background:linear-gradient(90deg,#1e88e5,#42a5f5); padding:18px 24px; color:#ffffff;">
              <h1 style="margin:0; font-size:20px;">Il tuo negozio</h1>
              <p style="margin:4px 0 0; font-size:13px; opacity:0.9;">
                Aggiornamento stato ordine #{ordine.id}
              </p>
            </td>
          </tr>

          <!-- CONTENUTO -->
          <tr>
            <td style="padding:24px;">
              <p style="margin:0 0 12px; font-size:14px; color:#444;">
                Ciao <strong>{ordine.cliente.username}</strong>,
              </p>

              <p style="margin:0 0 16px; font-size:14px; color:#444;">
                lo stato del tuo ordine <strong>#{ordine.id}</strong> è stato aggiornato.
              </p>

              <p style="margin:0 0 20px; font-size:14px; color:#444;">
                {testo_dinamico}
              </p>

              <table cellpadding="0" cellspacing="0" style="margin:0 0 20px; font-size:14px; color:#444;">
                <tr>
                  <td style="padding:4px 8px 4px 0; color:#777;">Stato precedente:</td>
                  <td style="padding:4px 0;"><strong>{vecchio_stato}</strong></td>
                </tr>
                <tr>
                  <td style="padding:4px 8px 4px 0; color:#777;">Nuovo stato:</td>
                  <td style="padding:4px 0;">
                    <span style="display:inline-block; padding:4px 10px; border-radius:999px; background-color:{bg}; color:{fg}; font-weight:bold; font-size:12px; letter-spacing:0.03em; text-transform:uppercase;">
                      {ordine.stato}
                    </span>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 20px; font-size:12px; color:#999;">
                Aggiornato il {ora_aggiornamento}
              </p>
    """

    if link_ordine:
        html += f"""
              <p style="margin:0 0 18px; font-size:14px; color:#444;">
                Puoi vedere tutti i dettagli del tuo ordine cliccando sul pulsante qui sotto:
              </p>

              <p style="margin:0 0 24px;">
                <a href="{link_ordine}"
                   style="display:inline-block; padding:10px 18px; background-color:#1e88e5; color:#ffffff;
                          text-decoration:none; border-radius:4px; font-size:14px;">
                  Vedi ordine
                </a>
              </p>
        """

    html += """
              <p style="margin:0 0 6px; font-size:13px; color:#666;">
                Grazie per aver acquistato da noi!
              </p>
              <p style="margin:0; font-size:12px; color:#999;">
                Se non hai richiesto questo aggiornamento, ignora questa email.
              </p>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#fafafa; padding:14px 24px; text-align:center; font-size:11px; color:#999;">
              © 2026 Il tuo negozio · Questo è un messaggio automatico, si prega di non rispondere.
              <span style="color:#999;">Privacy: i tuoi dati sono trattati in modo sicuro.</span>
              <a href="mailto:supporto@iltuonegozio.it">Contattaci</a>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    # INVIO CON SENDGRID
        # INVIO CON REQUESTS + CERTIFI
    try:
        data = {
            "personalizations": [{
                "to": [{"email": recipient}],
                "subject": subject
            }],
            "from": {"email": "testdev12311@outlook.com"},
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

        print(f"[EMAIL] Notifica HTML inviata a {recipient}")
        print("SENDGRID STATUS:", response.status_code)
        print("SENDGRID RESPONSE:", response.text)

    except Exception as e:
        print(f"[ERRORE EMAIL] {e}")