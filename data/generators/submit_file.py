"""Stand-in for the ingestion gateway: upload a submission to s3://raw and register it in the ledger.

What the real gateway does (and this script imitates):
  1. Check the file name against the contract pattern.
  2. Compute SHA-256 and compare it with the manifest.
  3. Reject duplicates (same hash already received).
  4. Store file + manifest in the Raw bucket (object lock) under a deterministic key.
  5. Register the submission in the ledger and return a receipt.

Usage:
    export S3_ENDPOINT=http://192.168.1.203:8080 AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
    export LEDGER_DSN=postgresql://ledger:<pw>@localhost:5432/ledger   # optional (kubectl port-forward)
    python data/generators/submit_file.py data/generators/output/FI001_LCR_2026-09_v1.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3

NAME_RE = re.compile(r"^(FI\d{3})_(LCR)_(\d{4}-\d{2})_v(\d+)\.csv$")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("file", type=Path)
    a = p.parse_args()

    m = NAME_RE.match(a.file.name)
    if not m:
        print(f"REJECTED: file name '{a.file.name}' does not match the contract pattern")
        return 2
    inst, rtype, period, version = m.group(1), m.group(2), m.group(3), int(m.group(4))

    manifest_path = a.file.with_name(a.file.name + ".manifest.json")
    if not manifest_path.exists():
        print("REJECTED: manifest missing")
        return 2
    manifest = json.loads(manifest_path.read_text())

    data = a.file.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != manifest["sha256"]:
        print("REJECTED: SHA-256 does not match manifest")
        return 2

    submission_id = f"{inst}-{rtype}-{period}-v{version}"
    key = f"{inst}/{rtype}/{period}/v{version}/{a.file.name}"
    s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name="us-east-1")

    dsn = os.environ.get("LEDGER_DSN")
    if dsn:
        import psycopg2

        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT submission_id FROM submission WHERE file_sha256 = %s", (sha,))
            dup = cur.fetchone()
            if dup:
                print(f"DUPLICATE: identical file already received as {dup[0]} (original receipt stands)")
                return 0

    s3.put_object(Bucket="raw", Key=key, Body=data, Metadata={"sha256": sha, "submission-id": submission_id})
    s3.put_object(Bucket="raw", Key=key + ".manifest.json", Body=manifest_path.read_bytes())

    if dsn:
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO submission (submission_id, institution_id, return_type, reporting_period,
                       version, file_name, file_sha256, raw_uri, record_count)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (submission_id, inst, rtype, period, version, a.file.name, sha,
                 f"s3://raw/{key}", manifest["record_count"]),
            )
            cur.execute(
                "INSERT INTO submission_event (submission_id, status) VALUES (%s, 'RECEIVED')",
                (submission_id,),
            )

    receipt = {
        "submission_id": submission_id,
        "status": "RECEIVED",
        "raw_uri": f"s3://raw/{key}",
        "sha256": sha,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(receipt, indent=2))
    print(f'\nTrigger the pipeline with conf: {{"submission_id": "{submission_id}", "raw_key": "{key}"}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
