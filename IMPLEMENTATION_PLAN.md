# Banking Web Application — Implementation Plan

> **Status:** Planning · **Stack:** HTML + Bootstrap · Python Flask · SQLite

---

## 1. Solution Overview

### Objective
Build a browser-based banking application that allows registered customers to log in, view their account balance, and perform deposit and withdrawal transactions through a simple, secure web interface.

### Scope
| In Scope | Out of Scope |
|---|---|
| Customer login / logout | User self-registration |
| View account balance | Multi-currency support |
| Deposit funds | Inter-account transfers |
| Withdraw funds | Admin / teller portal |
| Session-based authentication | Mobile native app |
| SQLite persistence | Third-party payment gateways |

### Users
- **Customer** — an existing bank account holder who authenticates and manages their own account via the web UI.

### Functional Requirements
1. A customer must be able to log in with a username and password.
2. After login, the customer must be redirected to a personal dashboard.
3. The dashboard must display the current account balance.
4. The customer must be able to deposit a positive monetary amount.
5. The customer must be able to withdraw a positive monetary amount, provided sufficient funds exist.
6. Every successful deposit or withdrawal must be reflected immediately in the displayed balance.
7. The customer must be able to log out, terminating their session.
8. Unauthenticated requests to protected pages must redirect to the login screen.

### Non-Functional Requirements
- **Security** — Passwords stored as hashed values (never plain-text); session tokens managed server-side.
- **Usability** — Responsive layout via Bootstrap; clear error messages for invalid credentials or insufficient funds.
- **Reliability** — All balance mutations wrapped in atomic database transactions to prevent partial updates.
- **Simplicity** — Minimal dependencies; no front-end JavaScript framework required.
- **Portability** — SQLite file-based database; no separate database server required.

### Assumptions
- Customer accounts are pre-seeded in the database by the workshop facilitator; there is no self-registration flow.
- The application runs on localhost for workshop/demo purposes; production hardening (HTTPS, secret management) is out of scope.
- A single account per customer is sufficient.
- Negative balances are not permitted.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        BROWSER                          │
│                                                         │
│  ┌────────────────────────────────────────────────┐    │
│  │          FRONTEND  (FRONTEND/)                  │    │
│  │  HTML templates  +  Bootstrap CSS               │    │
│  │  login.html · dashboard.html                    │    │
│  │  deposit.html · withdraw.html                   │    │
│  └──────────────┬──────────────────────────────────┘    │
└─────────────────┼───────────────────────────────────────┘
                  │  HTTP  (form POST / GET redirect)
┌─────────────────▼───────────────────────────────────────┐
│                  BACKEND  (BACKEND/)                    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Python Flask Application  (app.py)             │   │
│  │                                                  │   │
│  │  Route handlers                                  │   │
│  │  ├── /login    POST → authenticate user          │   │
│  │  ├── /dashboard GET → show balance               │   │
│  │  ├── /deposit  POST → add funds                  │   │
│  │  ├── /withdraw POST → deduct funds               │   │
│  │  └── /logout   GET  → clear session              │   │
│  │                                                  │   │
│  │  Services / helpers                              │   │
│  │  ├── auth.py   — password hashing, session mgmt  │   │
│  │  └── account.py — balance read, deposit/withdraw │   │
│  └──────────────────────────┬───────────────────────┘   │
└─────────────────────────────┼───────────────────────────┘
                              │  SQLite (Python sqlite3 / SQLAlchemy)
┌─────────────────────────────▼───────────────────────────┐
│                  DATABASE  (BACKEND/bank.db)            │
│                                                         │
│   customers  table — credentials + account data        │
│   transactions table — audit trail of deposits /       │
│                         withdrawals                     │
└─────────────────────────────────────────────────────────┘
```

### Frontend → Backend → Database Interaction

```
Browser                 Flask App               SQLite DB
   │                        │                        │
   │── GET /login ─────────►│                        │
   │◄─ 200 login.html ──────│                        │
   │                        │                        │
   │── POST /login ────────►│── SELECT customer ────►│
   │                        │◄─ row / None ──────────│
   │◄─ 302 /dashboard ──────│                        │
   │                        │                        │
   │── GET /dashboard ─────►│── SELECT balance ─────►│
   │◄─ 200 dashboard.html ──│◄─ balance value ────────│
   │                        │                        │
   │── POST /deposit ──────►│── UPDATE balance ─────►│
   │                        │── INSERT transaction ──►│
   │◄─ 302 /dashboard ──────│                        │
```

### Request Lifecycle
1. Browser sends an HTTP request (GET or form POST).
2. Flask routes the request to the matching view function.
3. The view function checks the server-side session for authentication; unauthenticated requests are redirected to `/login`.
4. Authenticated requests invoke a service helper that reads or writes the SQLite database.
5. The view function renders an HTML template (Jinja2) with the response data and returns it to the browser.
6. On a successful mutation (deposit/withdraw), Flask issues a `302 redirect` to `/dashboard` (POST–Redirect–GET pattern).

---

## 3. Component Design

### Frontend Responsibilities (`FRONTEND/`)
- Render all user-facing pages as server-rendered HTML templates (Jinja2).
- Apply Bootstrap for layout, form styling, navigation bar, and alert messages.
- Submit user input (credentials, amounts) via standard HTML forms using `POST`.
- Display server-provided data (balance, error messages, success confirmations) injected by Flask.
- No client-side business logic; no JavaScript required beyond Bootstrap's optional JS.

### Backend Responsibilities (`BACKEND/`)
- Own all business logic: authentication, balance calculation, transaction validation.
- Manage server-side sessions (Flask `session` object) to track logged-in customers.
- Validate all incoming form data (type checking, positive-amount enforcement, sufficient-funds check).
- Hash passwords before storage; compare hashes on login — never store or compare plain-text passwords.
- Execute all database reads and writes using parameterised queries to prevent SQL injection.
- Serve rendered HTML templates back to the browser.

### Database Responsibilities (`BACKEND/bank.db`)
- Persist customer credentials and current account balances.
- Persist a transaction log (deposits and withdrawals) for auditability.
- Enforce data integrity at the storage level (e.g. NOT NULL constraints, positive-amount check on the transactions table).
- Remain a single local file; no network access or separate process required.

---

## 4. Folder Structure

```
Banking-workshop IBM/
│
├── FRONTEND/                        # All browser-facing assets
│   ├── templates/                   # Jinja2 HTML templates (served by Flask)
│   │   ├── base.html                # Shared layout: navbar, Bootstrap CDN link
│   │   ├── login.html               # Login form
│   │   ├── dashboard.html           # Balance display + action buttons
│   │   ├── deposit.html             # Deposit amount form
│   │   └── withdraw.html            # Withdrawal amount form
│   └── static/                      # Optional: custom CSS or images
│       └── style.css
│
├── BACKEND/                         # All server-side code and data
│   ├── app.py                       # Flask application factory + route definitions
│   ├── auth.py                      # Authentication helpers (hashing, session check)
│   ├── account.py                   # Account service (get balance, deposit, withdraw)
│   ├── database.py                  # Database connection helper + init script
│   ├── seed.py                      # One-time script to seed demo customer accounts
│   ├── bank.db                      # SQLite database file (auto-created on first run)
│   └── requirements.txt             # Python dependencies (flask, werkzeug)
│
├── docs/                            # Workshop setup and CI documentation (existing)
│   └── demo-setup/
│
└── IMPLEMENTATION_PLAN.md           # This document
```

| Folder / File | Responsibility |
|---|---|
| `FRONTEND/templates/` | Jinja2 templates rendered by Flask and returned to the browser |
| `FRONTEND/static/` | Static assets (custom CSS, images) served directly by Flask |
| `BACKEND/app.py` | Entry point; registers all routes; creates the Flask app instance |
| `BACKEND/auth.py` | Password hashing, login verification, session guard decorator |
| `BACKEND/account.py` | Pure business logic for reading balance and applying transactions |
| `BACKEND/database.py` | Opens the SQLite connection; runs `CREATE TABLE IF NOT EXISTS` on startup |
| `BACKEND/seed.py` | Inserts demo users; run once before the workshop session |
| `BACKEND/bank.db` | SQLite data file; committed to repo for workshop convenience |
| `BACKEND/requirements.txt` | Pinned Python packages; used by CI and local setup |

---

## 5. Module Breakdown

### 5.1 Authentication Module
**Purpose:** Control who can access the application and manage session lifecycle.

| Concern | Approach |
|---|---|
| Password storage | Hashed with `werkzeug.security.generate_password_hash` |
| Login verification | `check_password_hash` comparison; no plain-text ever read |
| Session creation | Flask `session['user_id']` set on successful login |
| Route protection | A `login_required` decorator redirects unauthenticated requests to `/login` |
| Logout | `session.clear()` followed by redirect to `/login` |

**Routes involved:** `GET /login`, `POST /login`, `GET /logout`

---

### 5.2 Dashboard Module
**Purpose:** Landing page after login; shows current balance and navigation to transactions.

| Concern | Approach |
|---|---|
| Balance retrieval | Query database for the current account balance of `session['user_id']` |
| Display | Rendered in `dashboard.html` via Jinja2 template variable |
| Navigation | Bootstrap buttons linking to `/deposit` and `/withdraw` |

**Routes involved:** `GET /dashboard`

---

### 5.3 Account Management Module
**Purpose:** Maintain accurate and consistent account balance state.

| Concern | Approach |
|---|---|
| Balance read | Single SELECT query in `account.py` |
| Balance write | UPDATE query wrapped in a database transaction |
| Data integrity | Balance column has a CHECK constraint (`>= 0`) |

**Used by:** Transaction module's deposit and withdraw handlers.

---

### 5.4 Transaction Module
**Purpose:** Process deposits and withdrawals and record them for audit.

| Concern | Approach |
|---|---|
| Deposit | Validate amount > 0 → add to balance → insert transaction record |
| Withdrawal | Validate amount > 0 AND amount ≤ balance → subtract → insert record |
| Insufficient funds | Return error message to template; no database write occurs |
| Audit trail | Every successful mutation inserts a row in the `transactions` table |
| POST–Redirect–GET | After success, redirect to `/dashboard` to prevent form re-submission |

**Routes involved:** `GET /deposit`, `POST /deposit`, `GET /withdraw`, `POST /withdraw`

---

## 6. Implementation Roadmap

### Development Phases

| Phase | Name | Goal | Key Deliverables |
|---|---|---|---|
| **1** | Project Scaffolding | Establish runnable skeleton | Folder structure, `app.py` with Flask factory, `requirements.txt`, `database.py` initialising SQLite tables |
| **2** | Authentication | Secure login/logout flow working end-to-end | `auth.py`, `login.html`, `/login` + `/logout` routes, session guard decorator, `seed.py` with one demo user |
| **3** | Dashboard | Authenticated home screen showing balance | `dashboard.html`, `/dashboard` route, balance retrieval from DB |
| **4** | Transactions | Deposit and withdrawal fully functional | `account.py`, `deposit.html`, `withdraw.html`, `/deposit` + `/withdraw` routes, transaction table writes, error handling |
| **5** | UI Polish | Consistent, Bootstrap-styled interface | `base.html` layout, navbar, alert components for errors/success, responsive grid |
| **6** | Verification | Application works correctly end-to-end | Manual smoke test of all six features; fix any defects found |

### Estimated Effort

| Phase | Relative Effort |
|---|---|
| 1 — Scaffolding | Small |
| 2 — Authentication | Medium |
| 3 — Dashboard | Small |
| 4 — Transactions | Medium |
| 5 — UI Polish | Small |
| 6 — Verification | Small |

### Dependencies

```
Phase 1 (Scaffolding)
    └── Phase 2 (Authentication)
            └── Phase 3 (Dashboard)
                    └── Phase 4 (Transactions)
                            └── Phase 5 (UI Polish)
                                    └── Phase 6 (Verification)
```

Each phase depends on the previous phase being complete. Phases 3 and 4 can overlap once the session guard from Phase 2 is available.

---

*End of Implementation Plan*
