# AGENTS.md

Flask app providing a "free hosting" service for college (GCES) students: log in with a register number, upload a ZIP, and the extracted site is served at `/projects/<regno>/<project_name>/`.

## Run

- Install deps: `pip install -r requirements.txt` (Flask 3, Flask-Session, psycopg2-binary, requests)
- Start: `python app.py` — binds `0.0.0.0:7777`. No venv is checked in; create one locally.
- HTTPS is terminated by a Cloudflare tunnel in front of the origin; the app serves plain HTTP. `force_https` (app.py) redirects only when `X-Forwarded-Proto: http` — keep that logic, otherwise localhost dev redirect-loops.

## Database (local PostgreSQL)

- DB `ziphost`, role `MessReduction`, localhost:5432. Secrets come from `.env` (gitignored) — see `.env.example` for the key names. `app.py` loads them via `load_dotenv()`.
- One-time setup: `sudo bash setup_db.sh` (idempotent — rewrites pg_hba.conf localhost lines to `scram-sha-256`, creates role/db, applies `setup_db.sql`). It reads `DB_PASSWORD` from `.env` or the environment; bails if unset.
- Tables: `users`, `uploads`, `activity_logs`. `valid_registrations` exists in the schema but is dead code — auth no longer uses it (see below).

## Auth flow (current working tree, NOT yet committed)

- Registration and login verify `regno` + password against `https://hostel-api.gces.net.in/api/auth/verify-details` with a hardcoded `X-API-Key`. Verification service down → 503. First login of an unknown user auto-creates the account (login doubles as registration).
- regno format enforced: starts with `8301`, exactly 12 digits.
- Sessions: Flask-Session filesystem backend, 1h lifetime. Logout clears session.

## Gotchas

- `views/` is BOTH the template folder and the static folder (`static_url_path='/views'`). Frontend JS/CSS live in `views/scripts/` and `views/styles/`, split per page (`dashboard.html` + `dashboard.js`, etc.).
- The frontend always parses server responses as JSON — the global `@app.errorhandler` in app.py must keep returning JSON for every error, or clients break.
- ZIP uploads: project name must match `^[\w-]{3,50}$`; any entry containing `..`, `.env`, or `node_modules` is rejected; the top-level folder is stripped on extraction ("flattened").
- Projects live on disk at `projects/<regno>/<project_name>/` (gitignored runtime data); the `/projects/` route is public, everything else requires a session.
- All secrets (DB password, `SECRET_KEY`, API key) come from `.env` via `load_dotenv()` — keep them out of committed files. `setup_db.sh` also sources `.env`.

## Repo state

- `crack.py`, `settings.json`, `output.txt` are gitignored leftovers; `cmd.txt` is untracked noise. None are part of the app.