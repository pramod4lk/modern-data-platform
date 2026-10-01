# ADR-0001: Apache Iceberg as the table format

- **Status:** Accepted
- **Date:** 2026-10-01

## Context
The lakehouse needs ACID tables, schema evolution, time travel for audit, and support from many engines (Spark, Flink, Trino, future serving engines and cloud services) for a 10–15 year horizon.

## Options considered
1. **Apache Iceberg** — widest engine and cloud support; Apache-governed; Iceberg REST catalog standard.
2. **Delta Lake** — mature, best inside Databricks; development driven mainly by one vendor.
3. **Apache Hudi** — strong for high-frequency upserts; more complex to operate.

## Decision
Apache Iceberg, with Parquet data files.

## Consequences
- Any engine that speaks Iceberg can read the data without migration.
- Table maintenance (compaction, snapshot expiry) must be scheduled.
