import hashlib
from flask import Flask, request, jsonify, redirect
import psycopg2
from psycopg2 import pool
import random
import validators
from datetime import datetime, timedelta
from functools import wraps
import time

app = Flask(__name__)

# PostgreSQL connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 20,
    host="localhost",
    database="url_shortener",
    user="postgres",
    password="1234"
)

def get_db_connection():
    return db_pool.getconn()

def return_db_connection(conn):
    db_pool.putconn(conn)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('DROP TABLE IF EXISTS urls')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS urls (
                   long_url TEXT,
                   short_code TEXT PRIMARY KEY,
                   custom_alias BOOLEAN DEFAULT FALSE,
                   access_count INTEGER DEFAULT 0,
                   expires_at TIMESTAMP)''')
    conn.commit()
    cur.close()
    return_db_connection(conn)

# Simple in-memory rate limiting
rate_limit_cache = {}

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        now = time.time()
        
        if ip in rate_limit_cache:
            requests, timestamp = rate_limit_cache[ip]
            if now - timestamp < 60:  # 60 seconds window
                if requests >= 10:     # 10 requests limit
                    return jsonify({"error": "Rate limit exceeded"}), 429
                rate_limit_cache[ip] = (requests + 1, timestamp)
            else:
                rate_limit_cache[ip] = (1, now)
        else:
            rate_limit_cache[ip] = (1, now)
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/shorten', methods=['POST'])
@rate_limit
def shorten_url():
    data = request.get_json() or request.form
    
    long_url = data.get('url')
    custom_alias = data.get('alias')
    expires_in_days = data.get('expires_in_days')
    
    if not long_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    if not validators.url(long_url):
        return jsonify({'error': 'Invalid URL format'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT short_code FROM urls WHERE long_url = %s', (long_url,))
        existing_url = cur.fetchone()
        
        if existing_url and not custom_alias:
            short_code = existing_url[0]
            return jsonify({'short_url': f'http://127.0.0.1:5000/{short_code}'}), 200
        
        if custom_alias:
            cur.execute('SELECT 1 FROM urls WHERE short_code = %s', (custom_alias,))
            if cur.fetchone():
                return jsonify({'error': 'Custom alias already in use'}), 400
            short_code = custom_alias
            is_custom = True
        else:
            short_code = hashlib.md5(long_url.encode()).hexdigest()[:6]
            cur.execute('SELECT 1 FROM urls WHERE short_code = %s', (short_code,))
            while cur.fetchone():
                short_code = hashlib.md5((long_url + str(random.random())).encode()).hexdigest()[:6]
                cur.execute('SELECT 1 FROM urls WHERE short_code = %s', (short_code,))
            is_custom = False
        
        expires_at = datetime.now() + timedelta(days=int(expires_in_days)) if expires_in_days else None
        
        cur.execute(
            'INSERT INTO urls (long_url, short_code, custom_alias, access_count, expires_at) VALUES (%s, %s, %s, %s, %s)',
            (long_url, short_code, is_custom, 0, expires_at)
        )
        
        conn.commit()
        
        return jsonify({
            'original_url': long_url,
            'short_url': f'http://127.0.0.1:5000/{short_code}',
            'short_code': short_code,
            'expires_at': expires_at.isoformat() if expires_at else None
        }), 201
    
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/<short_code>', methods=['GET'])
@rate_limit
def redirect_url(short_code):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT long_url, access_count, expires_at FROM urls WHERE short_code = %s', (short_code,))
        row = cur.fetchone()

        if row:
            long_url, count, expires_at = row
            if expires_at and expires_at < datetime.now():
                return jsonify({'error': 'This link has expired'}), 410
            
            cur.execute('UPDATE urls SET access_count = %s WHERE short_code = %s', (count + 1, short_code))
            conn.commit()
            
            return redirect(long_url)
        else:
            return jsonify({'error': 'Short URL not found'}), 404
    
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/stats/<short_code>', methods=['GET'])
@rate_limit
def get_url_stats(short_code):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT long_url, short_code, access_count, expires_at FROM urls WHERE short_code = %s', (short_code,))
        row = cur.fetchone()
        
        if row:
            long_url, short_code, access_count, expires_at = row
            return jsonify({
                'original_url': long_url,
                'short_code': short_code,
                'access_count': access_count,
                'expires_at': expires_at.isoformat() if expires_at else None
            })
        else:
            return jsonify({'error': 'Short URL not found'}), 404
    
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/mappings', methods=['GET'])
@rate_limit
def get_all_mappings():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute('SELECT long_url, short_code, access_count, expires_at FROM urls')
        rows = cur.fetchall()
        
        mappings = [{
            "long_url": row[0],
            "short_code": row[1],
            "access_count": row[2],
            "expires_at": row[3].isoformat() if row[3] else None
        } for row in rows]
        
        return jsonify(mappings)
    
    finally:
        cur.close()
        return_db_connection(conn)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
