"""
seed.py — Populate the database with demo customer accounts.

Run this script once before the workshop:
    cd BACKEND
    python seed.py

Re-running is safe — it uses INSERT OR IGNORE so existing rows are skipped.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash
from database import get_db_connection, init_db

# Ensure tables exist before seeding
init_db()

DEMO_CUSTOMERS = [
    {"username": "alice",   "password": "password123", "balance": 1000.00},
    {"username": "bob",     "password": "securepass",  "balance": 2500.50},
    {"username": "charlie", "password": "bankingdemo", "balance": 500.00},
]

conn = get_db_connection()
with conn:
    for customer in DEMO_CUSTOMERS:
        hashed = generate_password_hash(customer["password"])
        conn.execute(
            "INSERT OR IGNORE INTO customers (username, password, balance) VALUES (?, ?, ?)",
            (customer["username"], hashed, customer["balance"]),
        )
conn.close()

print("Demo accounts seeded:")
for c in DEMO_CUSTOMERS:
    print(f"  username: {c['username']!r:12}  password: {c['password']!r:15}  starting balance: £{c['balance']:,.2f}")
