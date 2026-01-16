import stripe
import json
from flask import Blueprint, request, jsonify, current_app
from app.models import db, Ordine

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
        else:
            print("ORDINE NON TROVATO PER SESSION ID")

    return jsonify({'status': 'success'}), 200
