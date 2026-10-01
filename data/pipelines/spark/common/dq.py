"""Minimal rules-as-code engine: evaluates data/quality/<contract>/rules.yaml on a DataFrame
and appends one result row per rule to lakehouse.ops.dq_results.

Supported rule types: not_null, accepted_values, range, unique, aggregate_expression, row_expression.
Great Expectations / Soda can replace this engine later; the rules file and results table stay the same.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

QUALITY_DIR = Path("/opt/poc/quality")
RESULTS_TABLE = "lakehouse.ops.dq_results"


def load_rules(contract: str, stage: str) -> tuple[str, list[dict]]:
    spec = yaml.safe_load((QUALITY_DIR / contract / "rules.yaml").read_text())
    return spec["version"], [r for r in spec["rules"] if r["stage"] == stage]


def _failures(df: DataFrame, rule: dict) -> int:
    t = rule["type"]
    if t == "not_null":
        cond = None
        for c in rule["columns"]:
            cond = F.col(c).isNull() if cond is None else cond | F.col(c).isNull()
        return df.filter(cond).count()
    if t == "accepted_values":
        return df.filter(~F.col(rule["column"]).isin(rule["values"]) | F.col(rule["column"]).isNull()).count()
    if t == "range":
        cond = F.lit(False)
        if "min" in rule:
            cond = cond | (F.col(rule["column"]) < rule["min"])
        if "max" in rule:
            cond = cond | (F.col(rule["column"]) > rule["max"])
        return df.filter(cond).count()
    if t == "unique":
        return df.groupBy(*rule["columns"]).count().filter("count > 1").count()
    if t == "aggregate_expression":
        ok = df.agg(F.expr(rule["expression"]).alias("ok")).first()["ok"]
        return 0 if ok else 1
    if t == "row_expression":
        return df.filter(~F.expr(rule["expression"])).count()
    raise ValueError(f"Unknown rule type: {t}")


def run_rules(spark: SparkSession, df: DataFrame, contract: str, stage: str, submission_id: str) -> bool:
    """Run rules; write results; return True if no blocking rule failed."""
    version, rules = load_rules(contract, stage)
    total = df.count()
    now = datetime.now(timezone.utc)
    results, passed_all_blocking = [], True
    for r in rules:
        failed = _failures(df, r)
        outcome = "PASS" if failed == 0 else "FAIL"
        if outcome == "FAIL" and r["severity"] == "blocking":
            passed_all_blocking = False
        results.append((r["id"], version, contract, stage, submission_id, r["dimension"], r["severity"],
                        total, failed, outcome, now))
        print(f"[dq] {r['id']:<8} {r['severity']:<8} {outcome}  failed={failed}/{total}")

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
            rule_id STRING, rule_version STRING, contract STRING, stage STRING, submission_id STRING,
            dimension STRING, severity STRING, records_tested BIGINT, records_failed BIGINT,
            outcome STRING, checked_at TIMESTAMP)
        USING iceberg PARTITIONED BY (days(checked_at))""")
    cols = ["rule_id", "rule_version", "contract", "stage", "submission_id", "dimension", "severity",
            "records_tested", "records_failed", "outcome", "checked_at"]
    spark.createDataFrame(results, cols).writeTo(RESULTS_TABLE).append()
    return passed_all_blocking
