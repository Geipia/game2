from flask import Blueprint, request, jsonify
import sqlite3
from config import Config

stripe_webhook_bp = Blueprint('stripe_webhook', __name__)

@stripe_webhook_bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    event = None
    try:
        event = request.json
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    # Handle successful payment
    if event and event.get('type') == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        payment_id = session.get('id')
        with sqlite3.connect(Config.DATABASE) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET is_ready = 1 WHERE id = ?', (user_id,))
            c.execute('INSERT INTO payments (user_id, stripe_payment_id, status) VALUES (?, ?, ?)', (user_id, payment_id, 'completed'))
            conn.commit()
    return jsonify({'status': 'success'})
