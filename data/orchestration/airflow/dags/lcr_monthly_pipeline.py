"""LCR monthly pipeline: Raw -> structural validation -> Bronze (+ quality rules) -> Silver/Gold (dbt) -> publish.

Triggered per submission (manually, or later by a 'submission received' event), with conf:
    {"submission_id": "FI001-LCR-2026-09-v1",
     "raw_key": "FI001/LCR/2026-09/v1/FI001_LCR_2026-09_v1.csv"}

Spark steps run as SparkApplications (Spark Operator) in the lakehouse namespace.
dbt runs in the Airflow worker pod (images/airflow/Dockerfile) against Trino.
"""

from __future__ import annotations

from datetime import datetime, timedelta

try:  # Airflow 3
    from airflow.sdk import DAG, Param, task
except ImportError:  # Airflow 2.x
    from airflow import DAG
    from airflow.decorators import task
    from airflow.models.param import Param

try:
    from airflow.providers.standard.operators.bash import BashOperator
except ImportError:
    from airflow.operators.bash import BashOperator

from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
}

with DAG(
    dag_id="lcr_monthly_pipeline",
    description="Process one LCR submission from Raw to Gold",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,          # one Spark job at a time on the 6 GB compute VM
    default_args=DEFAULT_ARGS,
    tags=["lcr", "batch", "tier-1"],
    params={
        "submission_id": Param("FI001-LCR-2026-09-v1", type="string", pattern=r"^FI\d{3}-LCR-\d{4}-\d{2}-v\d+$"),
        "raw_key": Param("FI001/LCR/2026-09/v1/FI001_LCR_2026-09_v1.csv", type="string"),
    },
) as dag:

    validate_structure = SparkKubernetesOperator(
        task_id="validate_structure",
        namespace="lakehouse",
        application_file="spark-apps/validate-structure.yaml",
        get_logs=True,
        delete_on_termination=True,
        retries=0,  # structural failures are not transient
    )

    raw_to_bronze = SparkKubernetesOperator(
        task_id="raw_to_bronze",
        namespace="lakehouse",
        application_file="spark-apps/raw-to-bronze.yaml",
        get_logs=True,
        delete_on_termination=True,
    )

    dbt_build = BashOperator(
        task_id="dbt_build_silver_gold",
        bash_command=(
            "cd /opt/poc/dbt && "
            "dbt build --profiles-dir /opt/poc/dbt "
            "--select silver_lcr_monthly+ --fail-fast"
        ),
    )

    @task
    def publish(**context) -> None:
        """Mark the submission PUBLISHED in the ledger (connection id: ledger_db, optional)."""
        submission_id = context["params"]["submission_id"]
        try:
            from airflow.providers.postgres.hooks.postgres import PostgresHook

            hook = PostgresHook(postgres_conn_id="ledger_db")
            hook.run(
                "UPDATE submission SET status='PUBLISHED', updated_at=now() WHERE submission_id=%s;"
                "INSERT INTO submission_event (submission_id, status) VALUES (%s, 'PUBLISHED');",
                parameters=(submission_id, submission_id),
            )
        except Exception as exc:  # ledger is optional in the POC
            print(f"Ledger not updated ({exc}); submission {submission_id} published to Gold.")

    validate_structure >> raw_to_bronze >> dbt_build >> publish()
