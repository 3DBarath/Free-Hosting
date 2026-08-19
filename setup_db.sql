-- ============================================================
-- Free-Hosting schema for PostgreSQL (ziphost)
-- Applied by setup_db.sh. Idempotent: safe to run repeatedly.
-- ============================================================
BEGIN;

-- Valid registration number / date-of-birth combos used during
-- registration. Populate with your real student records, e.g.:
--   INSERT INTO valid_registrations (regno, dob) VALUES ('830123104011', '2005-04-12');
CREATE TABLE IF NOT EXISTS valid_registrations (
    regno VARCHAR(12) PRIMARY KEY,
    dob   DATE NOT NULL
);

-- Registered users
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    regno         VARCHAR(12) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Uploaded projects
CREATE TABLE IF NOT EXISTS uploads (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename       TEXT NOT NULL,
    project_folder TEXT NOT NULL,
    link           TEXT,
    upload_time    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_pinned      BOOLEAN NOT NULL DEFAULT FALSE
);

-- Audit trail of user actions
CREATE TABLE IF NOT EXISTS activity_logs (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action_type    TEXT,
    table_affected TEXT,
    record_id      INTEGER,
    description    TEXT,
    ip_address     TEXT,
    user_agent     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uploads_user_id      ON uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user   ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at);

COMMIT;
