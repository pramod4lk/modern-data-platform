#!/usr/bin/env bash
# End-to-end test (Milestone 3/6): generate -> submit -> run DAG -> check Gold.
# Prerequisites: S3_ENDPOINT/AWS_* exported, kubectl access, Airflow deployed, images built.
set -euo pipefail
PERIOD="${PERIOD:-2026-09}"
INST="${INST:-FI001}"
VERSION="${VERSION:-1}"
SUB="${INST}-LCR-${PERIOD}-v${VERSION}"
KEY="${INST}/LCR/${PERIOD}/v${VERSION}/${INST}_LCR_${PERIOD}_v${VERSION}.csv"

echo "1. Generate synthetic file"
python data/generators/generate_lcr_files.py --period "$PERIOD" --only "$INST" --version "$VERSION"

echo "2. Submit to Raw"
python data/generators/submit_file.py "data/generators/output/${INST}_LCR_${PERIOD}_v${VERSION}.csv"

echo "3. Trigger Airflow DAG"
AF_POD=$(kubectl -n orchestration get pod -l component=scheduler -o jsonpath='{.items[0].metadata.name}')
kubectl -n orchestration exec "$AF_POD" -c scheduler -- \
  airflow dags trigger lcr_monthly_pipeline --conf "{\"submission_id\":\"$SUB\",\"raw_key\":\"$KEY\"}"

echo "4. Wait for the run (check the Airflow UI), then press Enter"
read -r _

echo "5. Check Gold"
TRINO=$(kubectl -n lakehouse get pod -l app.kubernetes.io/component=coordinator -o jsonpath='{.items[0].metadata.name}')
kubectl -n lakehouse exec "$TRINO" -- trino --execute \
  "SELECT institution_id, reporting_period, lcr_ratio, submission_ids
   FROM iceberg.gold.gold_lcr_by_institution
   WHERE institution_id='$INST' AND reporting_period='$PERIOD'"
echo "6. Quality results"
kubectl -n lakehouse exec "$TRINO" -- trino --execute \
  "SELECT rule_id, severity, outcome, records_failed FROM iceberg.ops.dq_results WHERE submission_id='$SUB'"
