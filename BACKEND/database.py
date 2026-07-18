"""
database.py — SQLite connection helper and schema initialisation.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "bank.db")


def get_db_connection():
    """Open and return a new SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safer for concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they do not already exist."""
    conn = get_db_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    NOT NULL UNIQUE,
                password TEXT    NOT NULL,
                balance  REAL    NOT NULL DEFAULT 0.00
                             CHECK (balance >= 0)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                type        TEXT    NOT NULL CHECK (type IN ('deposit', 'withdrawal')),
                amount      REAL    NOT NULL CHECK (amount > 0),
                timestamp   TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)
    conn.close()
