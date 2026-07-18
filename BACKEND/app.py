"""
app.py — Flask application entry point.

Route handlers are defined here; business logic lives in auth.py and account.py.
"""
import os
import sys

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

# Make sure sibling modules (auth, account, database) are importable when the
# file is run directly from the BACKEND/ directory or from the project root.
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db
from auth import verify_login, login_required
import account as account_service


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "FRONTEND", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "FRONTEND", "static"),
)

# SECRET_KEY signs the session cookie.  In production, load from an env var.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")


# ---------------------------------------------------------------------------
# Initialise the database tables on startup
# ---------------------------------------------------------------------------

with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Routes — Authentication
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Root URL — redirect to dashboard (or login if not authenticated)."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, skip the login page.
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Server-side field-presence validation
        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        else:
            customer = verify_login(username, password)
            if customer is None:
                error = "Invalid username or password."
            else:
                session.clear()
                session["user_id"] = customer["id"]
                session["username"] = customer["username"]
                return redirect(url_for("dashboard"))

    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Routes — Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    balance = account_service.get_balance(session["user_id"])
    return render_template(
        "dashboard.html",
        username=session["username"],
        balance=balance,
    )


# ---------------------------------------------------------------------------
# Routes — Deposit
# ---------------------------------------------------------------------------

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    error = None
    amount_value = ""  # re-populate the field on error

    if request.method == "POST":
        raw = request.form.get("amount", "").strip()
        amount_value = raw

        if not raw:
            error = "Please enter an amount."
        else:
            try:
                amount = float(raw)
            except ValueError:
                error = "Amount must be a number."
            else:
                success, msg = account_service.deposit(session["user_id"], amount)
                if not success:
                    error = msg
                else:
                    flash("Deposit successful!", "success")
                    return redirect(url_for("dashboard"))

    return render_template("deposit.html", error=error, amount_value=amount_value)


# ---------------------------------------------------------------------------
# Routes — Withdraw
# ---------------------------------------------------------------------------

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    error = None
    amount_value = ""

    if request.method == "POST":
        raw = request.form.get("amount", "").strip()
        amount_value = raw

        if not raw:
            error = "Amount is required"
        else:
            try:
                amount = float(raw)
            except ValueError:
                error = "Amount must be a number."
            else:
                if amount <= 0:
                    error = "Amount must be greater than zero"
                else:
                    balance = account_service.get_balance(session["user_id"])
                    if amount > balance:
                        error = "Insufficient funds"
                    else:
                        success, msg = account_service.withdraw(session["user_id"], amount)
                        if not success:
                            error = msg
                        else:
                            flash("Withdrawal successful!", "success")
                            return redirect(url_for("dashboard"))

    return render_template("withdraw.html", error=error, amount_value=amount_value)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
