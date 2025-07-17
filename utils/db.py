import sqlite3
from flask import g
from config import Config

DATABASE = Config.DATABASE

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            photo_path TEXT,
            is_alive INTEGER DEFAULT 1,
            is_ready INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player1_id INTEGER,
            player2_id INTEGER,
            game_type TEXT,
            winner_id INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stripe_payment_id TEXT,
            status TEXT
        )''')
        conn.commit()

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
