# IBM Banking Web Application

A simple, fully-functional browser-based banking app built with **Python Flask**, **SQLite**, and **Bootstrap 5**.

---

## Project Structure

```
Banking-workshop IBM/
│
├── FRONTEND/
│   ├── templates/          # Jinja2 HTML templates
│   │   ├── base.html       # Shared navbar & Bootstrap layout
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── deposit.html
│   │   ├── withdraw.html
│   │   ├── 404.html
│   │   └── 500.html
│   └── static/
│       └── style.css       # Custom styles
│
├── BACKEND/
│   ├── app.py              # Flask app — all routes
│   ├── auth.py             # Login verification & login_required decorator
│   ├── account.py          # Balance read, deposit, withdraw logic
│   ├── database.py         # SQLite connection & schema initialisation
│   ├── seed.py             # One-time demo account seeder
│   ├── requirements.txt    # Python dependencies
│   └── bank.db             # SQLite file (auto-created on first run)
│
└── tests/
    └── test_banking.py     # Unit + integration tests (pytest)
```

---

## Quick Start

### 1 — Create & activate a virtual environment

```bash
# From the project root
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate
```

### 2 — Install dependencies

```bash
pip install -r BACKEND/requirements.txt
```

### 3 — Seed the demo accounts (run once)

```bash
cd BACKEND
python seed.py
```

This creates `bank.db` and inserts three demo customers:

| Username | Password      | Starting balance |
|----------|---------------|-----------------|
| alice    | password123   | £1,000.00       |
| bob      | securepass    | £2,500.50       |
| charlie  | bankingdemo   | £500.00         |

### 4 — Start the app

```bash
# Still inside BACKEND/
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Running the Tests

```bash
# From the project root (with venv active)
cd BACKEND
pytest ../tests/test_banking.py -v
```

The test suite uses an **in-memory SQLite database** — it does not touch `bank.db`.

---

## Features

| Feature | Detail |
|---------|--------|
| Login / Logout | Session-based authentication; passwords hashed with Werkzeug |
| Dashboard | Displays current balance for the logged-in customer |
| Deposit | Validates amount > 0; atomic UPDATE + INSERT |
| Withdraw | Validates amount > 0 and ≤ balance; atomic UPDATE + INSERT |
| Protected routes | `login_required` decorator redirects unauthenticated requests |
| POST–Redirect–GET | Prevents duplicate form submissions on browser refresh |
| Error pages | Custom 404 and 500 templates |

---

## Security Notes (Workshop Scope)

- Passwords are **never stored in plain-text** — only bcrypt-style hashes via `werkzeug.security`.
- All SQL queries use **parameterised statements** — no string concatenation (SQL injection prevention).
- `SECRET_KEY` should be loaded from an environment variable in production.
- `debug=False` must be set before any deployment.

---

*Made with IBM Bob*
