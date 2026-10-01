"""Generate synthetic monthly LCR return files, one per institution, plus a manifest each.

Usage:
    python data/generators/generate_lcr_files.py --period 2026-09 --institutions 5
    python data/generators/generate_lcr_files.py --period 2026-09 --only FI001 --version 2 --inject-error negative_amount

Output: data/generators/output/<FILE>.csv and <FILE>.csv.manifest.json  (git-ignored)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "output"
LINES = ["HQLA_L1", "HQLA_L2A", "HQLA_L2B", "OUT_RETAIL", "OUT_WHOLESALE", "OUT_OTHER", "IN_TOTAL"]
ERRORS = ["negative_amount", "missing_line", "bad_currency", "duplicate_row", "manifest_mismatch"]


def load_institutions() -> list[dict]:
    with open(REPO / "data/reference/institutions.csv", newline="") as f:
        return list(csv.DictReader(f))


def make_rows(inst: dict, period: str, rng: random.Random) -> list[dict]:
    scale = {"LARGE": 50_000_000, "MEDIUM": 8_000_000, "SMALL": 1_000_000}[inst["size_band"]]
    outflow_total = scale * rng.uniform(0.08, 0.15)
    target_lcr = rng.uniform(1.1, 2.5)                       # most institutions above 100%
    inflow = outflow_total * rng.uniform(0.2, 0.5)
    net_outflow = outflow_total - min(inflow, 0.75 * outflow_total)
    hqla = net_outflow * target_lcr
    values = {
        "HQLA_L1": hqla * 0.75,
        "HQLA_L2A": hqla * 0.20 / 0.85,
        "HQLA_L2B": hqla * 0.05 / 0.50,
        "OUT_RETAIL": outflow_total * 0.45,
        "OUT_WHOLESALE": outflow_total * 0.40,
        "OUT_OTHER": outflow_total * 0.15,
        "IN_TOTAL": inflow,
    }
    return [
        {"institution_id": inst["institution_id"], "reporting_period": period,
         "line_code": code, "currency": "MYR", "amount": round(values[code], 2)}
        for code in LINES
    ]


def inject(rows: list[dict], error: str) -> list[dict]:
    if error == "negative_amount":
        rows[0]["amount"] = -abs(rows[0]["amount"])
    elif error == "missing_line":
        rows = rows[:-1]
    elif error == "bad_currency":
        rows[1]["currency"] = "XXX"
    elif error == "duplicate_row":
        rows.append(dict(rows[2]))
    return rows


def write_file(rows: list[dict], inst_id: str, period: str, version: int, error: str | None) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{inst_id}_LCR_{period}_v{version}.csv"
    path = OUT_DIR / name
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    control_total = round(sum(float(r["amount"]) for r in rows), 2)
    record_count = len(rows)
    if error == "manifest_mismatch":
        record_count += 1
    manifest = {
        "file_name": name,
        "institution_id": inst_id,
        "return_type": "LCR",
        "reporting_period": period,
        "version": version,
        "record_count": record_count,
        "control_total": control_total,
        "sha256": sha,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": True,
    }
    (OUT_DIR / f"{name}.manifest.json").write_text(json.dumps(manifest, indent=2))
    return path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--period", required=True, help="Reporting period YYYY-MM")
    p.add_argument("--institutions", type=int, default=5, help="How many institutions (from FI001)")
    p.add_argument("--only", help="Single institution id, e.g. FI001")
    p.add_argument("--version", type=int, default=1)
    p.add_argument("--inject-error", choices=ERRORS)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()

    rng = random.Random(f"{a.seed}-{a.period}-{a.version}")
    insts = load_institutions()
    insts = [i for i in insts if i["institution_id"] == a.only] if a.only else insts[: a.institutions]
    for inst in insts:
        rows = make_rows(inst, a.period, rng)
        if a.inject_error:
            rows = inject(rows, a.inject_error)
        path = write_file(rows, inst["institution_id"], a.period, a.version, a.inject_error)
        print(f"wrote {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
