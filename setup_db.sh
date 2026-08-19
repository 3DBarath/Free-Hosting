#!/usr/bin/env bash
# ============================================================
# One-time PostgreSQL setup for Free-Hosting.
# RUN WITH SUDO:  sudo bash setup_db.sh
#
# - allows password auth on localhost (pg_hba.conf)
# - creates role MessReduction and database ziphost
# - applies the schema from setup_db.sql
# Safe to run repeatedly (idempotent).
# ============================================================
set -euo pipefail

DB_NAME="ziphost"
DB_USER="MessReduction"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load secrets from a repo-local .env (gitignored) if present, else rely on
# exported DB_PASSWORD / DB_PASS env vars.
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$SCRIPT_DIR/.env"
    set +a
fi
DB_PASS="${DB_PASSWORD:-${DB_PASS:-}}"

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must run as root:  sudo bash setup_db.sh" >&2
    exit 1
fi

if [ -z "$DB_PASS" ]; then
    echo "DB_PASSWORD not set. Create a .env file or export it before running." >&2
    exit 1
fi

PGDATA="${PGDATA:-/var/lib/pgsql/data}"
HBA="$PGDATA/pg_hba.conf"
# Replace the default 'ident' auth on the localhost lines so the app can
# connect as MessReduction with a password.
if [ -f "$HBA" ]; then
    sed -i -E 's#^(host\s+all\s+all\s+127\.0\.0\.1/32\s+)\S+$#\1scram-sha-256#' "$HBA" || true
    sed -i -E 's#^(host\s+all\s+all\s+::1/128\s+)\S+$#\1scram-sha-256#' "$HBA" || true
    # If no localhost host lines existed, append them.
    grep -qE '^host\s+all\s+all\s+127\.0\.0\.1/32' "$HBA" \
        || echo 'host    all             all             127.0.0.1/32            scram-sha-256' >> "$HBA"
    grep -qE '^host\s+all\s+all\s+::1/128' "$HBA" \
        || echo 'host    all             all             ::1/128                 scram-sha-256' >> "$HBA"
    echo "== pg_hba.conf: localhost set to scram-sha-256 =="
else
    echo "WARN: pg_hba.conf not found at $HBA; you must configure password auth yourself." >&2
fi

# Reload postgres config.
systemctl reload postgresql 2>/dev/null || runuser -u postgres -- pg_ctl reload -D "$PGDATA"

# --- 2) Create role and database (idempotent) ------------------------
echo "== Ensuring role $DB_USER =="
# Build the CREATE ROLE via format() and run it with \gexec. Avoids a DO
# block, because psql does not interpolate :'var' inside dollar-quoted text.
runuser -u postgres -- psql -v db_user="$DB_USER" -v db_pass="$DB_PASS" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'db_user', :'db_pass')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'db_user')\gexec
SQL

echo "== Ensuring database $DB_NAME =="
runuser -u postgres -- psql -v db_name="$DB_NAME" -v db_user="$DB_USER" <<'SQL'
SELECT 'CREATE DATABASE ' || quote_ident(:'db_name') || ' OWNER ' || quote_ident(:'db_user')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db_name')\gexec
SQL

# --- 3) Apply schema -------------------------------------------------
echo "== Applying schema from setup_db.sql =="
runuser -u postgres -- psql -d "$DB_NAME" -v ON_ERROR_STOP=1 < "$SCRIPT_DIR/setup_db.sql"

# --- 4) Grant the app user privileges on the tables/sequences ---------
# The schema is applied as postgres, so the objects are owned by postgres.
# Explicitly grant the app user full access (ownership would not cascade).
echo "== Granting privileges to $DB_USER =="
runuser -u postgres -- psql -d "$DB_NAME" -v ON_ERROR_STOP=1 -v db_user="$DB_USER" <<'SQL'
GRANT USAGE ON SCHEMA public TO :db_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO :db_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO :db_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO :db_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO :db_user;
SQL

echo
echo "Done. Database '$DB_NAME' is ready for user '$DB_USER'."
echo "Registration now verifies students via the hostel API, so no"
echo "valid_registrations seeding is needed."
echo "Start the app with:  venv/bin/python app.py"
