from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from flask_bcrypt import Bcrypt
from flask_session import Session
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
import sqlite3
import stripe
from config import Config
from utils.db import get_db, init_db, close_connection
from utils.scheduler import start_scheduler
from utils.stripe_webhook import stripe_webhook_bp
from PIL import Image

app = Flask(__name__)
app.config.from_object(Config)
Session(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app, manage_session=False)
app.register_blueprint(stripe_webhook_bp)
stripe.api_key = Config.STRIPE_SECRET_KEY

@app.before_request
def setup():
    init_db()

@app.teardown_appcontext
def teardown_db(exception):
    close_connection(exception)

@app.route('/')
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE is_ready = 1')
    count = c.fetchone()[0]
    cagnotte = count
    user_id = session.get('user_id')
    is_ready = session.get('is_ready', 0)
    user_is_registered = bool(is_ready)
    return render_template('index.html', cagnotte=cagnotte, user_id=user_id,
                           is_ready=is_ready, user_is_registered=user_is_registered)


# Inscription
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        photo = request.files.get('photo')
        if not (name and email and password and photo):
            flash('Tous les champs sont requis.', 'danger')
            return render_template('register.html')
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        filename = secure_filename(photo.filename)
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)
        img = Image.open(photo_path)
        img = img.resize((256, 256))
        img.save(photo_path)
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (name, email, password_hash, photo_path) VALUES (?, ?, ?, ?)',
                      (name, email, password_hash, photo_path))
            conn.commit()
            flash('Compte créé ! Payez pour valider votre inscription.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email déjà utilisé.', 'danger')
    return render_template('register.html')

# Connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not (email and password):
            flash('Email et mot de passe requis.', 'danger')
            return render_template('login.html')
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, password_hash, is_ready FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        if user and bcrypt.check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['is_ready'] = user[2]
            flash('Connecté !', 'success')
            return redirect(url_for('game'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

# Déconnexion
@app.route('/logout')
def logout():
    session.clear()
    flash('Déconnecté.', 'info')
    return redirect(url_for('index'))


# Après paiement, redirige l'utilisateur vers la page de jeu
@app.route('/payment_complete')
def payment_complete():
    """Mark the paying user as ready and send them to the game."""
    user_id = session.get('user_id')
    # If the session is lost, try retrieving the user from Stripe
    if not user_id:
        session_id = request.args.get('session_id')
        if session_id:
            try:
                checkout = stripe.checkout.Session.retrieve(session_id)
                user_id = checkout.get('client_reference_id')
                if user_id:
                    session['user_id'] = int(user_id)
            except Exception:
                pass
    if user_id:
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE users SET is_ready = 1 WHERE id = ?', (user_id,))
        conn.commit()
        session['is_ready'] = 1
        flash('Paiement confirmé. Bienvenue dans le jeu !', 'success')
        return redirect(url_for('game'))
    flash('Paiement enregistré. Connectez-vous pour jouer.', 'info')
    return redirect(url_for('index'))


# Jeu (protégé)
from functools import wraps
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Connectez-vous pour accéder au jeu.', 'warning')
            return redirect(url_for('login'))
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT is_ready FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        is_ready = row[0] if row else 0
        session['is_ready'] = is_ready
        if not is_ready:
            flash('Vous devez payer pour jouer. Utilisez le bouton Stripe sur la page d\'accueil.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/game', methods=['GET', 'POST'])
@login_required
def game():
    conn = get_db()
    c = conn.cursor()
    # Récupère tous les joueurs vivants et payés
    c.execute('SELECT id, name, email, photo_path, is_alive FROM users WHERE is_ready = 1 AND is_alive = 1')
    users = [dict(id=row[0], name=row[1], email=row[2], photo_path=row[3], is_alive=row[4]) for row in c.fetchall()]
    c.execute('SELECT COUNT(*) FROM users WHERE is_ready = 1')
    cagnotte = c.fetchone()[0]
    winner = None
    duel_opponent = None
    # Matchmaking : trouve un adversaire aléatoire (autre que soi)
    if session['user_id']:
        opponents = [u for u in users if u['id'] != session['user_id']]
        if opponents:
            import random
            duel_opponent = random.choice(opponents)
    # Mini-jeu réflexe contre un adversaire
    if request.method == 'POST' and duel_opponent:
        import random
        # Duel réflexe : le gagnant est aléatoire
        if random.random() > 0.5:
            winner = session['user_id']
            c.execute('UPDATE users SET is_alive = 0 WHERE id = ?', (duel_opponent['id'],))
            conn.commit()
            flash(f'Bravo, vous avez éliminé {duel_opponent["name"]} !', 'success')
        else:
            c.execute('UPDATE users SET is_alive = 0 WHERE id = ?', (session['user_id'],))
            conn.commit()
            flash('Vous êtes éliminé !', 'danger')
    return render_template('game.html', users=users, cagnotte=cagnotte, winner=winner, duel_opponent=duel_opponent)

@app.route('/vr')
def vr():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    users = [dict(id=row[0], name=row[1], email=row[2], photo_path=row[4], is_alive=row[5]) for row in c.fetchall()]
    c.execute('SELECT COUNT(*) FROM users WHERE is_ready = 1')
    cagnotte = c.fetchone()[0]
    return render_template('vr.html', users=users, cagnotte=cagnotte)

# SocketIO events
@socketio.on('connect')
def handle_connect():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE is_ready = 1')
    cagnotte = c.fetchone()[0]
    emit('update_cagnotte', cagnotte)

if __name__ == '__main__':
    start_scheduler()
    socketio.run(app, debug=True)
