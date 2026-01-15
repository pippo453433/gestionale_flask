import stripe
import json
from flask import Blueprint, request, jsonify, current_app
from app.models import db, Ordine

webhook_bp = Blueprint('webhook_bp', __name__)

@webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    print("WEBHOOK LOADED")
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config['STRIPE_WEBHOOK_SECRET']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        email = session.get('customer_email')

        ordine = Ordine.query.filter_by(email=email).order_by(Ordine.id.desc()).first()
        if ordine:
            ordine.pagato = True
            db.session.commit()

    return jsonify({'status': 'success'}), 200