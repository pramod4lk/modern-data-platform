"""Load a validated raw submission into the Bronze Iceberg table (append-only, all versions kept),
then run the Bronze quality rules. Blocking failures mark the submission QUARANTINED.

Usage:
    spark-submit raw_to_bronze.py --raw-key FI001/LCR/2026-09/v1/FI001_LCR_2026-09_v1.csv --submission-id FI001-LCR-2026-09-v1
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
from datetime import datetime, timezone

from pyspark.sql import types as T

from common.config import s3_client, spark_session
from common.dq import run_rules
from common.ledger import update_status

TABLE = "lakehouse.bronze.lcr_monthly"

SCHEMA = T.StructType([
    T.StructField("institution_id", T.StringType()),
    T.StructField("reporting_period", T.StringType()),
    T.StructField("line_code", T.StringType()),
    T.StructField("currency", T.StringType()),
    T.StructField("amount", T.DecimalType(20, 2)),
    # audit columns: every Bronze row traces back to its original file
    T.StructField("submission_id", T.StringType()),
    T.StructField("submission_version", T.IntegerType()),
    T.StructField("source_uri", T.StringType()),
    T.StructField("source_sha256", T.StringType()),
    T.StructField("loaded_at", T.TimestampType()),
])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-key", required=True)
    p.add_argument("--submission-id", required=True)
    a = p.parse_args()

    from decimal import Decimal

    data = s3_client().get_object(Bucket="raw", Key=a.raw_key)["Body"].read()
    sha = hashlib.sha256(data).hexdigest()
    version = int(a.submission_id.rsplit("-v", 1)[1])
    now = datetime.now(timezone.utc)
    rows = [
        (r["institution_id"], r["reporting_period"], r["line_code"], r["currency"], Decimal(r["amount"]),
         a.submission_id, version, f"s3://raw/{a.raw_key}", sha, now)
        for r in csv.DictReader(io.StringIO(data.decode("utf-8")))
    ]

    spark = spark_session("raw_to_bronze_lcr")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.bronze")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.ops")
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            institution_id STRING, reporting_period STRING, line_code STRING, currency STRING,
            amount DECIMAL(20,2), submission_id STRING, submission_version INT, source_uri STRING,
            source_sha256 STRING, loaded_at TIMESTAMP)
        USING iceberg PARTITIONED BY (reporting_period)
        TBLPROPERTIES ('write.format.default'='parquet', 'format-version'='2')""")

    # Idempotency: re-running the same submission replaces its rows instead of duplicating them.
    spark.sql(f"DELETE FROM {TABLE} WHERE submission_id = '{a.submission_id}'")
    df = spark.createDataFrame(rows, SCHEMA)
    df.writeTo(TABLE).append()
    print(f"loaded {len(rows)} rows for {a.submission_id} into {TABLE}")

    loaded = spark.table(TABLE).filter(f"submission_id = '{a.submission_id}'")
    ok = run_rules(spark, loaded, "lcr-monthly", "bronze", a.submission_id)
    update_status(a.submission_id, "ACCEPTED" if ok else "QUARANTINED",
                  None if ok else "blocking quality rule failed")
    spark.stop()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
