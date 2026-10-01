#!/usr/bin/env bash
# Smoke test: Trino is up, the Iceberg catalog is reachable, and time travel works on the smoke table.
# Run on k3s-server (or anywhere kubectl points at the cluster).
set -euo pipefail
NS=lakehouse
POD=$(kubectl -n $NS get pod -l app.kubernetes.io/component=coordinator -o jsonpath='{.items[0].metadata.name}')
q() { kubectl -n $NS exec "$POD" -- trino --output-format=TSV --execute "$1"; }

q "SELECT 1" >/dev/null && echo "OK   Trino responds"
q "SHOW SCHEMAS FROM iceberg" && echo "OK   Iceberg catalog reachable"
if q "SHOW TABLES FROM iceberg.smoke" | grep -q hello; then
  q "SELECT count(*) FROM iceberg.smoke.hello"
  SNAP=$(q 'SELECT snapshot_id FROM iceberg.smoke."hello$snapshots" ORDER BY committed_at LIMIT 1')
  q "SELECT count(*) FROM iceberg.smoke.hello FOR VERSION AS OF $SNAP" && echo "OK   time travel works"
else
  echo "INFO iceberg.smoke.hello not found - run data/pipelines/spark/smoke_test.py first"
fi
