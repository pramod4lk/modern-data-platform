# Payments stream (Milestone 4)

`payments_stream.sql` reads `payments.events.v1` from Kafka, applies a 5-minute watermark for late events, deduplicates on `event_id`, and writes:

- `lakehouse.bronze.payment_events` — every unique event
- `lakehouse.silver.payment_minute_stats` — 1-minute counts, values and failures per institution and payment system

Iceberg commits happen at each checkpoint (every 60 s), so data appears in Trino within about a minute.

## Running it

**Quick start (interactive):** start a Flink session cluster with the operator, open the SQL client inside the JobManager pod, and paste the rendered SQL.

**Packaged job:** build an image based on `flink:1.19` that adds
- the Flink Kubernetes Operator's example *SQL runner* jar (`sql-runner.jar`),
- `flink-sql-connector-kafka`, `iceberg-flink-runtime-1.19`, `iceberg-aws-bundle`,
- the rendered SQL under `/opt/flink/usrlib/sql-scripts/`,

then apply `flinkdeployment.yaml.example`. Check the Iceberg and Kafka connector versions that match your Flink version.

**Memory-saving alternative:** if `k3s-worker-2` is short of memory, implement the same logic with Spark Structured Streaming in the Spark image and skip the Flink operator.
