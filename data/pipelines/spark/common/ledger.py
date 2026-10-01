"""Optional submission-ledger updates. No-op when LEDGER_DSN is not set."""

from __future__ import annotations

import json
import os


def update_status(submission_id: str, status: str, reason: str | None = None, detail: dict | None = None) -> None:
    dsn = os.environ.get("LEDGER_DSN")
    if not dsn:
        print(f"[ledger] {submission_id} -> {status} ({reason or ''}) [LEDGER_DSN not set, not recorded]")
        return
    import psycopg2

    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE submission SET status=%s, status_reason=%s, updated_at=now() WHERE submission_id=%s",
            (status, reason, submission_id),
        )
        cur.execute(
            "INSERT INTO submission_event (submission_id, status, detail) VALUES (%s,%s,%s)",
            (submission_id, status, json.dumps(detail or {})),
        )
