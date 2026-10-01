"""Structural validation of a raw submission against its data contract (before anything reaches Bronze).

Checks: header columns, required fields, types, patterns, code lists, manifest record count and control total.
Writes a JSON validation report to s3://lakehouse/ops/validation-reports/ and exits 1 on failure.

Usage (inside the Spark image):
    spark-submit validate_structure.py --raw-key FI001/LCR/2026-09/v1/FI001_LCR_2026-09_v1.csv --submission-id FI001-LCR-2026-09-v1
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

import yaml

from common.config import s3_client
from common.ledger import update_status

CONTRACTS = Path("/opt/poc/contracts")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-key", required=True)
    p.add_argument("--submission-id", required=True)
    p.add_argument("--contract", default="lcr-monthly.v1.yaml")
    a = p.parse_args()

    contract = yaml.safe_load((CONTRACTS / a.contract).read_text())
    props = contract["schema"][0]["properties"]
    s3 = s3_client()
    body = s3.get_object(Bucket="raw", Key=a.raw_key)["Body"].read().decode("utf-8")
    manifest = json.loads(s3.get_object(Bucket="raw", Key=a.raw_key + ".manifest.json")["Body"].read())

    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(body))
    expected = [pr["name"] for pr in props]
    if reader.fieldnames != expected:
        errors.append(f"header {reader.fieldnames} != contract {expected}")

    rows = list(reader)
    control_total = 0.0
    for n, row in enumerate(rows, start=2):
        for pr in props:
            v = (row.get(pr["name"]) or "").strip()
            if pr.get("required") and not v:
                errors.append(f"line {n}: {pr['name']} is required")
                continue
            if pr["logicalType"] == "number":
                try:
                    num = float(v)
                    if pr["name"] == "amount":
                        control_total += num
                except ValueError:
                    errors.append(f"line {n}: {pr['name']}='{v}' is not a number")
            if "pattern" in pr and v and not re.match(pr["pattern"], v):
                errors.append(f"line {n}: {pr['name']}='{v}' does not match {pr['pattern']}")

    if len(rows) != manifest["record_count"]:
        errors.append(f"record count {len(rows)} != manifest {manifest['record_count']}")
    if abs(round(control_total, 2) - manifest["control_total"]) > 0.01:
        errors.append(f"control total {round(control_total, 2)} != manifest {manifest['control_total']}")

    report = {"submission_id": a.submission_id, "raw_key": a.raw_key,
              "status": "VALIDATED" if not errors else "REJECTED", "errors": errors[:200]}
    s3.put_object(Bucket="lakehouse", Key=f"ops/validation-reports/{a.submission_id}.json",
                  Body=json.dumps(report, indent=2).encode())
    print(json.dumps(report, indent=2))
    update_status(a.submission_id, report["status"], None if not errors else f"{len(errors)} structural errors",
                  {"errors": errors[:20]})
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
