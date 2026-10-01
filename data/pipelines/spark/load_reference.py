"""Load the synthetic reference data (institutions, code lists) into lakehouse.reference.* tables.

The CSV files are baked into the Spark image under /opt/poc/reference (see images/spark/Dockerfile),
or pass --reference-dir.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common.config import spark_session

FILES = {
    "institutions": "institutions.csv",
    "currencies": "code-lists/currencies.csv",
    "institution_types": "code-lists/institution-types.csv",
    "return_types": "code-lists/return-types.csv",
    "lcr_line_codes": "code-lists/lcr-line-codes.csv",
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reference-dir", default="/opt/poc/reference")
    a = p.parse_args()

    spark = spark_session("load_reference")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.reference")
    for table, rel in FILES.items():
        path = Path(a.reference_dir) / rel
        df = spark.read.option("header", True).option("inferSchema", True).csv(f"file://{path}")
        df.writeTo(f"lakehouse.reference.{table}").createOrReplace()
        print(f"lakehouse.reference.{table}: {df.count()} rows")
    spark.stop()


if __name__ == "__main__":
    main()
