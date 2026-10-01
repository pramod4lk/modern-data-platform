-- Submission ledger: one row per submission version.
-- Argo CD applies only the YAML files in this folder; apply this SQL by hand:
--   kubectl -n data-system exec -i pg-1 -- psql -U postgres -d ledger < ledger-schema.sql
CREATE TABLE IF NOT EXISTS submission (
    submission_id     TEXT PRIMARY KEY,          -- e.g. FI001-LCR-2026-09-v1
    institution_id    TEXT        NOT NULL,
    return_type       TEXT        NOT NULL,
    reporting_period  TEXT        NOT NULL,      -- YYYY-MM
    version           INTEGER     NOT NULL,
    file_name         TEXT        NOT NULL,
    file_sha256       TEXT        NOT NULL,
    raw_uri           TEXT        NOT NULL,
    record_count      INTEGER,
    status            TEXT        NOT NULL DEFAULT 'RECEIVED',
        -- RECEIVED, VALIDATED, REJECTED, QUARANTINED, ACCEPTED, PUBLISHED
    status_reason     TEXT,
    received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (institution_id, return_type, reporting_period, version),
    UNIQUE (file_sha256)                         -- duplicate upload detection
);

CREATE TABLE IF NOT EXISTS submission_event (
    event_id       BIGSERIAL PRIMARY KEY,
    submission_id  TEXT        NOT NULL REFERENCES submission(submission_id),
    status         TEXT        NOT NULL,
    detail         JSONB,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
