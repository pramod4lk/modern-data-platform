# POC milestones

Each milestone must work before starting the next. The **profile** line says which components to run (see `memory-budget.md`); the concepts to learn are in `learning-path.md`.

## M1 — Foundation
_Profile: none (infrastructure only)_

- [ ] 4 VMs created, static IPs, reachable by hostname
- [ ] k3s: `kubectl get nodes` shows 3 nodes `Ready`
- [ ] MicroCeph healthy (`ceph -s` → `HEALTH_OK` or `HEALTH_WARN` for single node only)
- [ ] Buckets `raw`, `lakehouse`, `archive` created; `raw` has object lock

**Done when:** a file can be uploaded to and read from `s3://raw/` from a pod in k3s.

## M2 — Lakehouse core
_Profile: core_

- [ ] PostgreSQL (CloudNativePG) running
- [ ] Polaris catalog running, catalog `lakehouse` pointing at `s3://lakehouse/`
- [ ] Trino with Iceberg REST catalog configured
- [ ] Spark job writes an Iceberg table

**Done when:** a table written by Spark is queried by Trino, and `SELECT * FROM t FOR VERSION AS OF ...` (time travel) works.

## M3 — Batch pipeline
_Profile: batch_

- [ ] Synthetic LCR files generated for 5 institutions
- [ ] Raw → Bronze (Spark), Bronze → Silver → Gold (dbt on Trino)
- [ ] Quality rules run; results in `lakehouse.ops.dq_results`
- [ ] Airflow DAG runs the whole chain

**Done when:** one Airflow run takes a new file to Gold with quality results recorded.

## M4 — Streaming
_Profile: streaming_

- [ ] Strimzi Kafka (1 broker, KRaft) running
- [ ] Payment events produced against a registered schema
- [ ] Flink job writes events to `lakehouse.bronze.payment_events`

**Done when:** events appear in Trino within ~2 minutes of being produced.

## M5 — Serving and governance
_Profile: serve-govern (+ observe)_

- [ ] Superset dashboard on a Gold table
- [ ] Keycloak SSO for Superset (and Airflow, if time allows)
- [ ] OpenMetadata shows tables, owners, lineage Raw → Gold
- [ ] Stretch: Ranger masks a PII column in Trino

## M6 — Proof tests
_Profile: full_

- [ ] Resubmitted (corrected) file becomes a new version; old version still queryable
- [ ] Iceberg rollback to a previous snapshot
- [ ] Kill a Trino/Spark pod mid-run; pipeline recovers on retry
- [ ] Onboard FI002 by adding `onboarding/institutions/FI002.yaml` only

## POC success criteria

One synthetic institution's file and one event stream reach a Gold table and a dashboard, with lineage, quality results and time travel all visible.
