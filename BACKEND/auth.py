"""
auth.py — Login verification and session-guard decorator.
"""
from functools import wraps

from flask import session, redirect, url_for
from werkzeug.security import check_password_hash

from database import get_db_connection


# ---------------------------------------------------------------------------
# Login verification
# ---------------------------------------------------------------------------

def verify_login(username: str, password: str):
    """
    Check username/password against the database.

    Returns the customer row on success, or None on failure.
    The same None is returned whether the username is wrong or the
    password is wrong — this prevents user-enumeration attacks.
    """
    conn = get_db_connection()
    customer = conn.execute(
        "SELECT * FROM customers WHERE username = ?", (username,)
    ).fetchone()

    if customer is None:
        return None
    if not check_password_hash(customer["password"], password):
        return None
    return customer


# ---------------------------------------------------------------------------
# Login-required decorator
# ---------------------------------------------------------------------------

def login_required(f):
    """Redirect to /login if the user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated
