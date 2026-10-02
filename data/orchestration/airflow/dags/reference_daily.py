"""Scheduled Spark job: reload synthetic reference data every day at 02:00 Malaysia time.

Learning example for scheduling (see docs/learning-path.md, Milestone 3).
max_active_runs=1 also keeps only one Spark job on the 6 GB compute VM at a time.
"""

from __future__ import annotations

from datetime import timedelta

import pendulum

try:  # Airflow 3
    from airflow.sdk import DAG
except ImportError:  # Airflow 2.x
    from airflow import DAG

from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator

with DAG(
    dag_id="reference_daily",
    description="Reload reference data into lakehouse.reference.*",
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 10, 1, tz="Asia/Kuala_Lumpur"),
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "data-engineering", "retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["reference", "spark", "scheduled"],
) as dag:
    SparkKubernetesOperator(
        task_id="load_reference",
        namespace="lakehouse",
        application_file="spark-apps/load-reference.yaml",
        get_logs=True,
        delete_on_termination=True,
    )
