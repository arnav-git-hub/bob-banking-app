"""
tests/test_banking.py

Unit and integration tests for the IBM Banking Application.

Run from the project root (with venv active):
    cd BACKEND && pytest ../tests/test_banking.py -v
  or
    python -m pytest tests/test_banking.py -v
"""
import os
import sys
import sqlite3
import pytest

# Ensure BACKEND/ is on the path so we can import the modules.
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "BACKEND")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

from werkzeug.security import generate_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_in_memory_db():
    """Return a seeded in-memory SQLite connection ready for testing."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE customers (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            balance  REAL    NOT NULL DEFAULT 0.00 CHECK (balance >= 0)
        )
    """)
    conn.execute("""
        CREATE TABLE transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            type        TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "INSERT INTO customers (username, password, balance) VALUES (?, ?, ?)",
        ("testuser", generate_password_hash("testpass"), 1000.00),
    )
    conn.commit()
    return conn


def get_customer_id(conn):
    return conn.execute(
        "SELECT id FROM customers WHERE username = 'testuser'"
    ).fetchone()["id"]


def get_balance_from(conn, customer_id):
    return float(
        conn.execute(
            "SELECT balance FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()["balance"]
    )


# ---------------------------------------------------------------------------
# Pytest fixture — Flask test client with isolated in-memory DB
# ---------------------------------------------------------------------------

@pytest.fixture()
def flask_client():
    """
    Fresh Flask test client + in-memory DB for every test that requests it.
    Monkeypatches get_db_connection in all backend modules.
    """
    import database as db_module
    import account as account_module
    import auth as auth_module
    import app as app_module

    test_conn = make_in_memory_db()

    def _conn():
        return test_conn

    db_module.get_db_connection = _conn
    account_module.get_db_connection = _conn
    auth_module.get_db_connection = _conn

    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    with app_module.app.test_client() as client:
        yield client, test_conn


@pytest.fixture()
def logged_in_client(flask_client):
    """Flask test client that is already logged in as testuser."""
    client, conn = flask_client
    client.post("/login", data={"username": "testuser", "password": "testpass"})
    return client, conn


# ---------------------------------------------------------------------------
# Unit tests — auth helpers (no DB needed)
# ---------------------------------------------------------------------------

class TestAuthHelpers:
    def test_correct_password_matches(self):
        from werkzeug.security import generate_password_hash, check_password_hash
        hashed = generate_password_hash("mypassword")
        assert check_password_hash(hashed, "mypassword") is True

    def test_wrong_password_does_not_match(self):
        from werkzeug.security import generate_password_hash, check_password_hash
        hashed = generate_password_hash("mypassword")
        assert check_password_hash(hashed, "wrongpass") is False

    def test_different_passwords_hash_differently(self):
        from werkzeug.security import generate_password_hash
        h1 = generate_password_hash("abc")
        h2 = generate_password_hash("abc")
        # Hashes include a random salt — should differ each call
        assert h1 != h2


# ---------------------------------------------------------------------------
# Unit tests — account service
# ---------------------------------------------------------------------------

class TestAccountService:
    @pytest.fixture(autouse=True)
    def setup_db(self, monkeypatch):
        self.conn = make_in_memory_db()
        self.customer_id = get_customer_id(self.conn)

        import account as account_module
        monkeypatch.setattr(account_module, "get_db_connection", lambda: self.conn)

    def _balance(self):
        return get_balance_from(self.conn, self.customer_id)

    # --- get_balance ---

    def test_get_balance_returns_initial_balance(self):
        import account
        assert account.get_balance(self.customer_id) == 1000.00

    # --- deposit ---

    def test_deposit_increases_balance(self):
        import account
        ok, err = account.deposit(self.customer_id, 200.00)
        assert ok is True and err is None
        assert self._balance() == 1200.00

    def test_deposit_records_transaction(self):
        import account
        account.deposit(self.customer_id, 150.00)
        row = self.conn.execute(
            "SELECT * FROM transactions WHERE customer_id = ?", (self.customer_id,)
        ).fetchone()
        assert row["type"] == "deposit"
        assert row["amount"] == 150.00

    def test_deposit_zero_rejected(self):
        import account
        ok, _ = account.deposit(self.customer_id, 0)
        assert ok is False
        assert self._balance() == 1000.00

    def test_deposit_negative_rejected(self):
        import account
        ok, _ = account.deposit(self.customer_id, -50)
        assert ok is False
        assert self._balance() == 1000.00

    def test_deposit_over_max_rejected(self):
        import account
        ok, err = account.deposit(self.customer_id, 2_000_000)
        assert ok is False
        assert "maximum" in err.lower()

    # --- withdraw ---

    def test_withdraw_decreases_balance(self):
        import account
        ok, err = account.withdraw(self.customer_id, 400.00)
        assert ok is True and err is None
        assert self._balance() == 600.00

    def test_withdraw_full_balance(self):
        import account
        ok, err = account.withdraw(self.customer_id, 1000.00)
        assert ok is True
        assert self._balance() == 0.00

    def test_withdraw_records_transaction(self):
        import account
        account.withdraw(self.customer_id, 100.00)
        row = self.conn.execute(
            "SELECT * FROM transactions WHERE customer_id = ?", (self.customer_id,)
        ).fetchone()
        assert row["type"] == "withdrawal"
        assert row["amount"] == 100.00

    def test_withdraw_insufficient_funds_rejected(self):
        import account
        ok, err = account.withdraw(self.customer_id, 9999.00)
        assert ok is False
        assert "insufficient" in err.lower()
        assert self._balance() == 1000.00  # unchanged

    def test_withdraw_zero_rejected(self):
        import account
        ok, _ = account.withdraw(self.customer_id, 0)
        assert ok is False
        assert self._balance() == 1000.00

    def test_withdraw_negative_rejected(self):
        import account
        ok, _ = account.withdraw(self.customer_id, -100)
        assert ok is False
        assert self._balance() == 1000.00


# ---------------------------------------------------------------------------
# Integration tests — Flask test client
# ---------------------------------------------------------------------------

class TestLoginFlow:
    def test_login_page_loads(self, flask_client):
        client, _ = flask_client
        resp = client.get("/login")
        assert resp.status_code == 200
        assert b"Sign In" in resp.data

    def test_valid_login_redirects_to_dashboard(self, flask_client):
        client, _ = flask_client
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "testpass"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]

    def test_invalid_password_shows_error(self, flask_client):
        client, _ = flask_client
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "wrongpass"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Invalid username or password" in resp.data

    def test_nonexistent_user_shows_error(self, flask_client):
        client, _ = flask_client
        resp = client.post(
            "/login",
            data={"username": "nobody", "password": "pass"},
            follow_redirects=True,
        )
        assert b"Invalid username or password" in resp.data

    def test_empty_username_shows_error(self, flask_client):
        client, _ = flask_client
        resp = client.post(
            "/login", data={"username": "", "password": "pass"}, follow_redirects=True
        )
        assert b"required" in resp.data.lower()

    def test_empty_password_shows_error(self, flask_client):
        client, _ = flask_client
        resp = client.post(
            "/login", data={"username": "testuser", "password": ""}, follow_redirects=True
        )
        assert b"required" in resp.data.lower()


class TestProtectedRoutes:
    def test_dashboard_requires_login(self, flask_client):
        client, _ = flask_client
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_deposit_requires_login(self, flask_client):
        client, _ = flask_client
        resp = client.get("/deposit", follow_redirects=False)
        assert resp.status_code == 302

    def test_withdraw_requires_login(self, flask_client):
        client, _ = flask_client
        resp = client.get("/withdraw", follow_redirects=False)
        assert resp.status_code == 302


class TestDepositFlow:
    def test_deposit_form_loads(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.get("/deposit")
        assert resp.status_code == 200
        assert b"Deposit" in resp.data

    def test_valid_deposit_redirects_to_dashboard(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.post("/deposit", data={"amount": "100"}, follow_redirects=False)
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]

    def test_blank_deposit_shows_error(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.post("/deposit", data={"amount": ""}, follow_redirects=True)
        assert b"Please enter an amount" in resp.data

    def test_non_numeric_deposit_shows_error(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.post("/deposit", data={"amount": "abc"}, follow_redirects=True)
        assert b"must be a number" in resp.data

    def test_zero_deposit_shows_error(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.post("/deposit", data={"amount": "0"}, follow_redirects=True)
        assert b"greater than zero" in resp.data

    def test_negative_deposit_shows_error(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.post("/deposit", data={"amount": "-50"}, follow_redirects=True)
        assert b"greater than zero" in resp.data

    def test_deposit_increases_balance(self, logged_in_client):
        client, conn = logged_in_client
        cid = get_customer_id(conn)
        before = get_balance_from(conn, cid)
        client.post("/deposit", data={"amount": "250"})
        after = get_balance_from(conn, cid)
        assert after == before + 250.00


class TestWithdrawFlow:
    def test_withdraw_form_loads(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.get("/withdraw")
        assert resp.status_code == 200
        assert b"Withdraw" in resp.data

    def test_valid_withdrawal_redirects_to_dashboard(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.post("/withdraw", data={"amount": "50"}, follow_redirects=False)
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]

    def test_blank_withdraw_shows_error(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.post("/withdraw", data={"amount": ""}, follow_redirects=True)
        assert b"Please enter an amount" in resp.data

    def test_insufficient_funds_shows_error(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.post("/withdraw", data={"amount": "999999"}, follow_redirects=True)
        assert b"insufficient" in resp.data.lower()

    def test_withdrawal_decreases_balance(self, logged_in_client):
        client, conn = logged_in_client
        cid = get_customer_id(conn)
        before = get_balance_from(conn, cid)
        client.post("/withdraw", data={"amount": "100"})
        after = get_balance_from(conn, cid)
        assert after == before - 100.00


class TestLogoutFlow:
    def test_logout_redirects_to_login(self, logged_in_client):
        client, _ = logged_in_client
        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_dashboard_inaccessible_after_logout(self, logged_in_client):
        client, _ = logged_in_client
        client.get("/logout")
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
