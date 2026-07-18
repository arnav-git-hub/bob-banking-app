"""
account.py — Account service: balance reads, deposits, withdrawals.

All database mutations are wrapped in explicit transactions so that
the UPDATE to the balance and the INSERT into transactions always
succeed or fail together.

Note: connections are NOT explicitly closed here. Each call opens
a fresh connection via get_db_connection(); the caller (or the
teardown_appcontext hook in app.py) is responsible for lifecycle
management. This also makes the module easier to test — unit tests
can monkeypatch get_db_connection to return a shared in-memory
connection without having it closed mid-test.
"""
from database import get_db_connection

MAX_SINGLE_TRANSACTION = 1_000_000.00  # guard against unreasonable amounts


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------

def get_balance(customer_id: int) -> float:
    """Return the current balance for *customer_id*."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT balance FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    return float(row["balance"])


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------

def deposit(customer_id: int, amount: float):
    """
    Add *amount* to the customer's balance and record the transaction.

    Returns (True, None) on success, or (False, error_message) on failure.
    """
    if amount <= 0:
        return False, "Deposit amount must be greater than zero."
    if amount > MAX_SINGLE_TRANSACTION:
        return False, "Amount exceeds the maximum single deposit limit."

    conn = get_db_connection()
    with conn:  # automatic commit / rollback
        conn.execute(
            "UPDATE customers SET balance = balance + ? WHERE id = ?",
            (amount, customer_id),
        )
        conn.execute(
            "INSERT INTO transactions (customer_id, type, amount) VALUES (?, 'deposit', ?)",
            (customer_id, amount),
        )
    return True, None


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------

def withdraw(customer_id: int, amount: float):
    """
    Subtract *amount* from the customer's balance and record the transaction.

    Returns (True, None) on success, or (False, error_message) on failure.
    Insufficient-funds check happens before any database write.
    """
    if amount <= 0:
        return False, "Withdrawal amount must be greater than zero."
    if amount > MAX_SINGLE_TRANSACTION:
        return False, "Amount exceeds the maximum single withdrawal limit."

    conn = get_db_connection()
    balance = float(
        conn.execute(
            "SELECT balance FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()["balance"]
    )

    if amount > balance:
        return False, (
            f"Insufficient funds. Your current balance is £{balance:,.2f}."
        )

    with conn:
        conn.execute(
            "UPDATE customers SET balance = balance - ? WHERE id = ?",
            (amount, customer_id),
        )
        conn.execute(
            "INSERT INTO transactions (customer_id, type, amount) VALUES (?, 'withdrawal', ?)",
            (customer_id, amount),
        )
    return True, None
