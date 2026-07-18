# Step-by-Step Implementation Guide
# Banking Web Application — Flask + SQLite + Bootstrap

> **Purpose:** Plain-English instructions explaining *what* to build and *how the logic works* at each step — not the finished code.
> **Stack:** Python Flask · SQLite · Bootstrap · Jinja2 HTML Templates

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Backend Implementation](#2-backend-implementation)
3. [Frontend Implementation](#3-frontend-implementation)
4. [Integration Steps](#4-integration-steps)
5. [Validation Rules](#5-validation-rules)
6. [Testing](#6-testing)
7. [Deployment](#7-deployment)

---

## 1. Environment Setup

### 1.1 Install Python

- Make sure Python 3.9 or higher is installed on your machine.
- Confirm the installation works by checking the Python version from your terminal.
- Python comes with `pip`, which is the package installer you will use to add libraries.

### 1.2 Create a Virtual Environment

- A virtual environment keeps this project's dependencies isolated from other Python projects on your machine.
- Inside your project root folder, create a virtual environment using the `venv` module that ships with Python.
- This creates a new subfolder (commonly named `venv`) that holds a private copy of Python and all packages you install.
- You must **activate** the virtual environment before installing packages or running the app. When activated, your terminal prompt will show the environment name.
- Always activate the environment at the start of every development session.

### 1.3 Install Project Dependencies

- With the virtual environment active, install the required libraries using pip.
- The two core libraries are:
  - **Flask** — the web framework that handles routing, templating, and sessions.
  - **Werkzeug** — ships with Flask and provides the password hashing utilities you will use to store passwords safely.
- Create a `requirements.txt` file inside `BACKEND/` that lists these two packages with their versions. This file lets any developer (or CI system) recreate the exact same environment with a single install command.

### 1.4 Confirm Flask Is Working

- Create a minimal `app.py` that starts Flask and returns "Hello, World" for any request.
- Run the file and visit `http://127.0.0.1:5000` in a browser.
- If you see the response, Flask is set up correctly. Delete the test route before moving on.

---

## 2. Backend Implementation

### 2.1 Create the Flask Application Entry Point (`app.py`)

**What it does:** Acts as the front door to the entire server. Every browser request arrives here first.

- Import Flask and the session module at the top of the file.
- Create a Flask application instance.
- Set a `SECRET_KEY` on the app — this is a long random string Flask uses to sign the session cookie. Without it, sessions will not work. For local development, any hard-coded string is fine; in production this must be an environment secret.
- Tell Flask where to find your HTML templates by pointing `template_folder` at `FRONTEND/templates/`.
- Tell Flask where to find static files (CSS, images) by pointing `static_folder` at `FRONTEND/static/`.
- At the bottom of the file, include the standard `if __name__ == "__main__"` guard that runs the Flask development server when you execute the file directly.
- Import and register your route functions from other modules (you will write these modules next).

### 2.2 Database Setup (`database.py`)

**What it does:** Connects to SQLite and ensures the tables exist before the app handles any request.

- Write a function `get_db_connection` that opens a connection to the `bank.db` SQLite file inside `BACKEND/`. SQLite creates the file automatically if it does not exist yet.
- Set the connection's `row_factory` to `sqlite3.Row` so that query results can be accessed like dictionaries (by column name), not just by index number.
- Write a second function `init_db` that runs `CREATE TABLE IF NOT EXISTS` statements for two tables:
  1. **customers** — stores the unique customer id, their username, their hashed password, and their current account balance. The balance column should have a constraint that prevents it going below zero.
  2. **transactions** — stores an auto-incrementing id, the customer id it belongs to, the type of transaction (deposit or withdrawal), the amount, and a timestamp. Transactions are append-only; they are never updated or deleted.
- Call `init_db` once when the Flask app starts up so the tables are always ready.

### 2.3 Seed Demo Accounts (`seed.py`)

**What it does:** Populates the database with test users so the workshop can begin immediately.

- This is a standalone script you run once from the terminal, not part of the web application itself.
- Import the password hasher from Werkzeug.
- Connect to the database and insert one or more rows into the customers table.
- Before inserting, hash each customer's plain-text password using `generate_password_hash`. Store only the hash — never the original password.
- Give each customer a starting balance (e.g. 1000.00).
- After running this script, the database is ready for use.

### 2.4 Authentication Helpers (`auth.py`)

**What it does:** Contains all logic for verifying identity and controlling access.

**Login verification function:**
- Accept a username and a plain-text password as inputs.
- Query the customers table for a row matching the given username.
- If no row is found, return a failure signal — do not reveal whether the username or password was wrong (just say "invalid credentials").
- If a row is found, use Werkzeug's `check_password_hash` to compare the stored hash with the password the user just typed.
- If the hashes match, return the customer's data (especially their id). If they do not match, return a failure signal.

**Login-required decorator:**
- A decorator is a wrapper you apply to any route function that needs the user to be logged in.
- The decorator checks whether `user_id` exists in the Flask session.
- If it does, the request proceeds normally to the route function.
- If it does not, the decorator immediately redirects the browser to the `/login` page.
- Apply this decorator to every route except `/login` and `/logout`.

**Session management:**
- On successful login: store the customer's id in `session['user_id']` and their username in `session['username']`.
- On logout: call `session.clear()` to wipe all session data, then redirect to `/login`.

### 2.5 Account Service (`account.py`)

**What it does:** The single place where balance reads and writes happen — all other code calls these functions instead of writing SQL directly.

**Get balance function:**
- Accept a customer id.
- Run a SELECT query to fetch the current balance for that customer.
- Return the balance value as a number.

**Deposit function:**
- Accept a customer id and an amount.
- Begin a database transaction.
- Run an UPDATE query that adds the amount to the customer's current balance.
- Run an INSERT query to record the deposit in the transactions table (type = "deposit", amount = the value deposited, timestamp = now).
- Commit the transaction. Both the UPDATE and INSERT succeed together or neither does.
- Return a success signal.

**Withdraw function:**
- Accept a customer id and an amount.
- First, read the current balance (call the get balance function).
- Check that the amount is less than or equal to the current balance. If not, return an "insufficient funds" error signal without touching the database.
- If sufficient funds exist, begin a database transaction.
- Run an UPDATE query that subtracts the amount from the balance.
- Run an INSERT query to record the withdrawal in the transactions table (type = "withdrawal").
- Commit. Return a success signal.

### 2.6 Route Handlers (inside `app.py`)

**What it does:** Maps URLs to Python functions. Each function handles one page or action.

**GET /login:**
- Simply render and return the `login.html` template.
- If the user is already logged in (session has a user_id), redirect them straight to `/dashboard` instead.

**POST /login:**
- Read the username and password from the submitted form data.
- Call the login verification function from `auth.py`.
- If login fails: re-render `login.html` and pass an error message to the template.
- If login succeeds: store the user id in the session and redirect to `/dashboard`.

**GET /dashboard** *(login required)*:
- Read `session['user_id']`.
- Call the get balance function from `account.py`.
- Render `dashboard.html`, passing in the balance and the customer's username.

**GET /deposit** *(login required)*:
- Render the `deposit.html` template (just the empty form).

**POST /deposit** *(login required)*:
- Read the amount from the submitted form.
- Validate: the value must be convertible to a number and must be greater than zero.
- If validation fails: re-render `deposit.html` with an error message.
- If valid: call the deposit function from `account.py`.
- After success: redirect to `/dashboard` (POST–Redirect–GET pattern — this prevents the form from re-submitting if the user clicks refresh).

**GET /withdraw** *(login required)*:
- Render the `withdraw.html` template.

**POST /withdraw** *(login required)*:
- Read the amount from the submitted form.
- Validate: must be a positive number.
- Call the withdraw function from `account.py`.
- If the function returns "insufficient funds": re-render `withdraw.html` with the error.
- If success: redirect to `/dashboard`.

**GET /logout** *(login required)*:
- Call `session.clear()`.
- Redirect to `/login`.

### 2.7 Error Handling

- Wrap form-data parsing (converting strings to numbers) in try/except blocks. If a user submits a non-numeric amount, catch the error and show a user-friendly message like "Please enter a valid amount."
- Register a custom 404 handler in Flask so that visiting an unknown URL shows a helpful page rather than a raw Flask error.
- Register a custom 500 handler for unexpected server errors. During development, Flask's debug mode will show full tracebacks — turn this off before any deployment.
- All validation errors should be passed into the template as a message variable and displayed using a Bootstrap alert component so the user sees clear feedback.

---

## 3. Frontend Implementation

### 3.1 Base Layout Template (`base.html`)

**What it does:** Defines the shared skeleton that all other pages inherit so that the navigation bar and Bootstrap styles are in one place.

- Link to the Bootstrap CSS via its CDN URL in the `<head>` section. This means no Bootstrap files need to be downloaded or hosted locally.
- Add a responsive navigation bar using Bootstrap's navbar component. It should show the application name on the left. When a user is logged in, show their username and a Logout button on the right. When not logged in, show nothing (or just the app name).
- Use Jinja2's template inheritance: define a `{% block content %}{% endblock %}` placeholder in the body. Child templates fill this block with their own content.
- Optionally link to `style.css` in `FRONTEND/static/` for any minor custom styling.

### 3.2 Login Page (`login.html`)

**What it does:** Collects the customer's credentials.

- Extends `base.html`.
- Centered card layout using Bootstrap's grid (use a column that is 4–6 units wide on medium screens, centered with `offset`).
- A form with two fields: username (text input) and password (password input).
- A Submit button.
- If an error message was passed from Flask, display it above the form inside a red Bootstrap alert (`alert-danger`).
- The form's `action` points to `/login` and the `method` is `POST`.

### 3.3 Dashboard Page (`dashboard.html`)

**What it does:** The home screen after login — shows the balance and navigation buttons.

- Extends `base.html`.
- Display a welcome message using the username from the session (passed by Flask).
- Show the current balance in a prominent Bootstrap card or `jumbotron`-style panel.
- Format the balance as a currency value (e.g. "£1,000.00").
- Two Bootstrap buttons below the balance: **Deposit** (links to `/deposit`) and **Withdraw** (links to `/withdraw`).
- If a success message was passed (e.g. after a successful deposit), display it in a green Bootstrap alert (`alert-success`) at the top of the page.

### 3.4 Deposit Form (`deposit.html`)

**What it does:** Lets the customer enter the amount they want to deposit.

- Extends `base.html`.
- A form with a single numeric input field labelled "Amount".
- The `type` attribute of the input should be `number` with a minimum value of `0.01` and a `step` of `0.01` to guide the browser into accepting decimal currency values.
- A Submit button labelled "Deposit".
- A Cancel/Back link that returns to `/dashboard`.
- If an error message exists, show it in a red Bootstrap alert above the form.
- Form `action` is `/deposit`, method is `POST`.

### 3.5 Withdraw Form (`withdraw.html`)

**What it does:** Identical in structure to the deposit form, but for withdrawals.

- Extends `base.html`.
- Same layout as `deposit.html` — a numeric input, Submit button, and Back link.
- The error message is especially important here because insufficient-funds rejections need to be communicated clearly.
- Form `action` is `/withdraw`, method is `POST`.

### 3.6 Bootstrap Layout Principles to Apply Throughout

- Use Bootstrap's **container** class to center and pad all page content.
- Use Bootstrap's **grid** (`row` / `col-*`) to control column widths.
- Use Bootstrap **form-control** classes on all input elements for consistent styling.
- Use Bootstrap **btn btn-primary** / **btn btn-danger** etc. on buttons.
- Use Bootstrap **alert** classes for all error and success messages — this makes them visually distinct.
- Use Bootstrap's **navbar** and **nav-link** for the navigation bar.

---

## 4. Integration Steps

### 4.1 Connect Flask to SQLite

- Flask does not manage database connections automatically. You must open a connection at the start of a request and close it at the end.
- Use Flask's `g` object (a request-scoped store) to hold the open connection. Write a helper that checks if a connection already exists on `g` — if not, it opens one; if yes, it returns the existing one. This ensures only one connection is opened per request.
- Use Flask's `teardown_appcontext` hook to automatically close the connection after every request completes, even if an error occurred.
- Import and call your `init_db` function inside the Flask `app_context` at startup so tables are created before the first request.

### 4.2 Connect Frontend Templates to Flask Routes

- Flask serves templates using `render_template("filename.html", variable=value)`. The variables you pass become available as `{{ variable }}` in the Jinja2 template.
- Forms post to Flask routes using the HTML `<form action="/route" method="POST">` pattern. Flask reads the submitted data from `request.form["field_name"]`.
- Redirects from Flask (`redirect(url_for("function_name"))`) go back to the browser as HTTP 302 responses, which the browser automatically follows. This is the POST–Redirect–GET pattern that prevents duplicate form submissions.
- Static files (CSS) are referenced in templates using Flask's `url_for("static", filename="style.css")` helper — this generates the correct URL regardless of where the app is hosted.

### 4.3 Session Flow End-to-End

- When a customer logs in successfully, the server stores their id in a signed, encrypted cookie (the Flask session).
- On every subsequent request, Flask reads the cookie, verifies its signature, and makes the session data available as a dictionary.
- The `login_required` decorator reads `session['user_id']` — if present, the user is authenticated; if missing, they are redirected to login.
- Logging out clears the session dictionary, which effectively invalidates the cookie.

### 4.4 Template Folder Location

- Flask needs to know where your templates live. When creating the app instance in `app.py`, pass `template_folder="../FRONTEND/templates"` (relative to where `app.py` sits).
- Similarly pass `static_folder="../FRONTEND/static"` for CSS.
- This keeps the frontend and backend in their separate folders while Flask can still find them.

---

## 5. Validation Rules

### 5.1 Login Validation

| What to check | Rule | What to do if it fails |
|---|---|---|
| Username field is not empty | Must contain at least one character | Redisplay the login form with the message "Username is required" |
| Password field is not empty | Must contain at least one character | Redisplay the login form with the message "Password is required" |
| Username exists in the database | SELECT query must return a row | Show a generic "Invalid username or password" message — do not say which field was wrong (this prevents user enumeration) |
| Password matches stored hash | `check_password_hash` returns True | Same generic "Invalid username or password" message |

### 5.2 Deposit Validation

| What to check | Rule | What to do if it fails |
|---|---|---|
| Amount field is not empty | Must not be blank | Show "Please enter an amount" |
| Amount is a valid number | Must be parseable as a float | Show "Amount must be a number" |
| Amount is positive | Must be greater than 0.00 | Show "Deposit amount must be greater than zero" |
| Amount is reasonable | Optionally cap at a large maximum (e.g. 1,000,000) to prevent overflow | Show "Amount exceeds the maximum single deposit limit" |

### 5.3 Withdrawal Validation

| What to check | Rule | What to do if it fails |
|---|---|---|
| Amount field is not empty | Must not be blank | Show "Please enter an amount" |
| Amount is a valid number | Must be parseable as a float | Show "Amount must be a number" |
| Amount is positive | Must be greater than 0.00 | Show "Withdrawal amount must be greater than zero" |
| Sufficient funds | Amount must be ≤ current balance | Show "Insufficient funds. Your current balance is £X.XX" |

### 5.4 General Validation Principles

- Always validate on the **server side** (in Flask), never rely on browser-side HTML attributes alone (`min`, `max`, `required`) — these can be bypassed.
- Re-populate the form with the last-entered value when showing a validation error so the user does not have to retype everything.
- Use Python's `try/except` when converting form strings to numbers — a string like "abc" will throw a `ValueError` that you should catch and treat as a validation failure.
- All validation happens *before* any database operation. No partial writes occur.

---

## 6. Testing

### 6.1 Unit Tests

Unit tests check individual functions in isolation without running the web server or touching the database.

**What to test in `auth.py`:**
- Verify that `check_password_hash` correctly identifies a matching password.
- Verify that a wrong password returns a failure signal.
- Verify that looking up a non-existent username returns a failure signal.

**What to test in `account.py`:**
- Call the get balance function with a known customer id and verify it returns the expected value.
- Call deposit with a positive amount and verify the balance increases by exactly that amount.
- Call withdraw with a valid amount and verify the balance decreases by exactly that amount.
- Call withdraw with an amount greater than the balance and verify it returns an error signal and does *not* change the balance.
- Call deposit or withdraw with zero or a negative number and verify they are rejected.

**How to structure unit tests:**
- Use Python's built-in `unittest` module or the `pytest` library.
- For tests that touch the database, use an **in-memory SQLite database** (`:memory:`) so tests are fast and do not pollute the real `bank.db`.
- Create a fresh database and seed a test customer before each test method. Tear it down after.

### 6.2 Integration Tests

Integration tests check that the full request–response cycle works correctly by sending requests to Flask and inspecting the HTML responses.

**How to set up:**
- Flask ships with a built-in **test client** that simulates a browser without opening a real browser.
- In your test setup, create the Flask app in testing mode and get a test client from it.
- Use a separate in-memory database for tests so they do not affect real data.

**What to test:**
- **Login flow:** POST valid credentials → expect a 302 redirect to `/dashboard`. POST invalid credentials → expect a 200 response that contains the error message text.
- **Dashboard access without login:** GET `/dashboard` without a session → expect a redirect to `/login`.
- **Dashboard access with login:** Simulate a logged-in session → GET `/dashboard` → expect the balance to appear in the response HTML.
- **Deposit flow:** Simulate login → POST a valid amount to `/deposit` → expect a redirect to `/dashboard` → GET `/dashboard` → expect the balance to have increased.
- **Withdraw flow:** Simulate login → POST a valid amount to `/withdraw` → expect redirect and decreased balance.
- **Withdraw with insufficient funds:** POST an amount larger than the balance → expect the `withdraw.html` response to contain the "Insufficient funds" error text.
- **Logout:** Simulate login → GET `/logout` → expect redirect to `/login` → GET `/dashboard` → expect redirect back to `/login` (session is gone).

### 6.3 Manual Testing Checklist

Work through this checklist in a real browser after starting the server:

**Authentication:**
- [ ] Visit `/dashboard` without logging in — you should be redirected to `/login`.
- [ ] Submit the login form with blank fields — the form should reject submission or show an error.
- [ ] Submit the login form with a wrong password — you should see "Invalid username or password" and stay on the login page.
- [ ] Submit correct credentials — you should land on the dashboard showing the right username and balance.

**Dashboard:**
- [ ] The correct account balance is displayed.
- [ ] The Deposit and Withdraw buttons are visible and clickable.
- [ ] The navigation bar shows your username and a Logout link.

**Deposit:**
- [ ] Click Deposit — you see the deposit form.
- [ ] Submit the form with a blank amount — you see an error.
- [ ] Submit the form with "abc" — you see an error.
- [ ] Submit the form with `-50` or `0` — you see an error.
- [ ] Submit the form with a valid positive amount — you are redirected to the dashboard and the balance has increased by exactly that amount.
- [ ] Press the browser Back button after a successful deposit — the form should not re-submit (POST–Redirect–GET prevents this).

**Withdrawal:**
- [ ] Submit a valid withdrawal that is less than the balance — balance decreases correctly.
- [ ] Submit a withdrawal that equals the balance — balance goes to zero, no error.
- [ ] Submit a withdrawal greater than the balance — you see the "Insufficient funds" message and the balance is unchanged.

**Logout:**
- [ ] Click Logout — you are sent to the login page.
- [ ] Press browser Back — you are not granted access to the dashboard.
- [ ] Visit `/dashboard` directly after logout — you are redirected to `/login`.

---

## 7. Deployment

### 7.1 Running Locally

1. Open a terminal in the project root.
2. Activate your virtual environment.
3. Move into the `BACKEND/` directory.
4. Run the seed script once to populate the database with demo accounts (skip on subsequent runs).
5. Run `app.py` to start the Flask development server.
6. Flask will print a local URL (e.g. `http://127.0.0.1:5000`). Open this in a browser.
7. Log in with one of the demo credentials created by the seed script.

**Things to remember for local development:**
- Flask's built-in server is single-threaded and not suitable for real users — it is only for development and demos.
- If you restart the server, the session cookies become invalid because the `SECRET_KEY` may change. Users will be logged out and need to log in again.
- The `bank.db` file accumulates all data between runs. To reset to a clean state, delete `bank.db` and re-run the seed script.

### 7.2 Production Considerations

The following items are **out of scope** for the workshop but should be addressed before any real-world deployment:

**Secret management:**
- Never hard-code `SECRET_KEY` in source code. Load it from an environment variable or a secrets manager. A compromised secret key means session cookies can be forged.

**HTTPS:**
- All traffic must go over HTTPS. Run Flask behind a reverse proxy (Nginx or Apache) that handles TLS termination, or deploy to a platform that provides HTTPS automatically (e.g. Heroku, Render, Railway).

**Production WSGI server:**
- Replace Flask's built-in development server with a production-grade WSGI server such as **Gunicorn** (Linux/Mac) or **Waitress** (Windows-compatible). Add it to `requirements.txt`.
- Example: `gunicorn -w 4 app:app` runs Flask with 4 worker processes.

**Database:**
- SQLite is fine for low concurrency. For higher traffic, consider migrating to PostgreSQL.
- Back up `bank.db` regularly (it is a single file — copying it is enough).

**Debug mode:**
- Ensure `debug=False` when running in production. Debug mode exposes an interactive Python console to anyone who can trigger an error — this is a critical security risk.

**Environment variables:**
- Use a `.env` file (loaded by a library like `python-dotenv`) or your hosting platform's environment variable panel to store `SECRET_KEY`, database path, and any other configuration that differs between environments.

---

*End of Step-by-Step Implementation Guide*
