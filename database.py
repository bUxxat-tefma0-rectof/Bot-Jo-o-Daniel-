import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('joao_store.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.0,
                referral_code TEXT,
                referred_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de produtos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                category TEXT DEFAULT 'logins',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                price REAL,
                credentials TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        ''')
        
        # Tabela de transações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                type TEXT,
                payment_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        cursor = self.conn.cursor()
        referral_code = f"REF{user_id}"
        cursor.execute(
            'INSERT OR IGNORE INTO users (user_id, username, first_name, referral_code) VALUES (?, ?, ?, ?)',
            (user_id, username, first_name, referral_code)
        )
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    def update_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def add_product(self, name, description, price, stock, category='logins'):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO products (name, description, price, stock, category) VALUES (?, ?, ?, ?, ?)',
            (name, description, price, stock, category)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_products(self, category=None):
        cursor = self.conn.cursor()
        if category:
            cursor.execute('SELECT * FROM products WHERE category = ? AND is_active = TRUE', (category,))
        else:
            cursor.execute('SELECT * FROM products WHERE is_active = TRUE')
        return cursor.fetchall()
    
    def get_product(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        return cursor.fetchone()
    
    def create_order(self, user_id, product_id, credentials):
        cursor = self.conn.cursor()
        product = self.get_product(product_id)
        cursor.execute(
            'INSERT INTO orders (user_id, product_id, price, credentials) VALUES (?, ?, ?, ?)',
            (user_id, product_id, product[3], credentials)
        )
        # Atualizar estoque
        cursor.execute('UPDATE products SET stock = stock - 1 WHERE id = ?', (product_id,))
        self.conn.commit()
        return cursor.lastrowid
    
    def add_transaction(self, user_id, amount, payment_id, type='deposit'):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO transactions (user_id, amount, type, payment_id) VALUES (?, ?, ?, ?)',
            (user_id, amount, type, payment_id)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def complete_transaction(self, payment_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE payment_id = ?', (payment_id,))
        transaction = cursor.fetchone()
        
        if transaction and transaction[5] == 'pending':
            cursor.execute('UPDATE transactions SET status = "completed" WHERE payment_id = ?', (payment_id,))
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (transaction[2], transaction[1]))
            self.conn.commit()
            return True
        return False
