-- Streaming path: Kafka (payments.events.v1) -> dedup + watermark -> Iceberg Bronze + 1-minute aggregates.
-- Placeholders ${...} are substituted at deploy time (Flink SQL does not read environment variables):
--   envsubst < payments_stream.sql > /tmp/job.sql

SET 'execution.checkpointing.interval' = '60s';   -- Iceberg commits happen on checkpoints
SET 'pipeline.name' = 'payments-stream';

CREATE CATALOG lakehouse WITH (
  'type' = 'iceberg',
  'catalog-type' = 'rest',
  'uri' = 'http://polaris.data-system.svc.cluster.local:8181/api/catalog',
  'warehouse' = 'lakehouse',
  'credential' = '${POLARIS_CLIENT_ID}:${POLARIS_CLIENT_SECRET}',
  'scope' = 'PRINCIPAL_ROLE:ALL',
  'io-impl' = 'org.apache.iceberg.aws.s3.S3FileIO',
  's3.endpoint' = '${S3_ENDPOINT}',
  's3.path-style-access' = 'true',
  'client.region' = 'us-east-1'
);

CREATE TEMPORARY TABLE payment_events_src (
  event_id        STRING,
  institution_id  STRING,
  event_time      BIGINT,
  payment_system  STRING,
  direction       STRING,
  amount          DOUBLE,
  currency        STRING,
  status          STRING,
  ts AS TO_TIMESTAMP_LTZ(event_time, 3),
  proc_time AS PROCTIME(),
  WATERMARK FOR ts AS ts - INTERVAL '5' MINUTE          -- accept events up to 5 minutes late
) WITH (
  'connector' = 'kafka',
  'topic' = 'payments.events.v1',
  'properties.bootstrap.servers' = 'poc-kafka-kafka-bootstrap.streaming.svc:9092',
  'properties.group.id' = 'flink-payments-stream',
  'scan.startup.mode' = 'earliest-offset',
  'format' = 'json',
  'json.ignore-parse-errors' = 'false'
);

CREATE DATABASE IF NOT EXISTS lakehouse.bronze;
CREATE DATABASE IF NOT EXISTS lakehouse.silver;

CREATE TABLE IF NOT EXISTS lakehouse.bronze.payment_events (
  event_id STRING, institution_id STRING, event_ts TIMESTAMP(3), payment_system STRING,
  direction STRING, amount DOUBLE, currency STRING, status STRING, ingested_at TIMESTAMP(3)
) PARTITIONED BY (institution_id);

CREATE TABLE IF NOT EXISTS lakehouse.silver.payment_minute_stats (
  window_start TIMESTAMP(3), window_end TIMESTAMP(3), institution_id STRING, payment_system STRING,
  event_count BIGINT, total_amount DOUBLE, failed_count BIGINT
);

-- Deduplicate on event_id (keep the first occurrence), then write both outputs in one job.
CREATE TEMPORARY VIEW payment_events_dedup AS
SELECT event_id, institution_id, ts, payment_system, direction, amount, currency, status
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY proc_time ASC) AS rn
  FROM payment_events_src
) WHERE rn = 1;

EXECUTE STATEMENT SET
BEGIN
  INSERT INTO lakehouse.bronze.payment_events
  SELECT event_id, institution_id, CAST(ts AS TIMESTAMP(3)), payment_system, direction, amount, currency,
         status, CAST(CURRENT_TIMESTAMP AS TIMESTAMP(3))
  FROM payment_events_dedup;

  INSERT INTO lakehouse.silver.payment_minute_stats
  SELECT window_start, window_end, institution_id, payment_system,
         COUNT(*), SUM(amount), SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END)
  FROM TABLE(TUMBLE(TABLE payment_events_src, DESCRIPTOR(ts), INTERVAL '1' MINUTE))
  GROUP BY window_start, window_end, institution_id, payment_system;
END;
