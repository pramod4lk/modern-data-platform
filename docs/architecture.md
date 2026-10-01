# Architecture and POC scope

This POC implements a small, working slice of the **Central Bank Modern Data Platform — Target-State Enterprise Architecture** (the full architecture document is maintained separately; add its link here).

## Target design in one paragraph

One governed, open-standard lakehouse: Apache Iceberg tables on S3-compatible object storage (Ceph), fed by Kafka and by file/API submissions, processed by Spark (batch) and Flink (streaming), orchestrated by Airflow, queried through Trino, governed through OpenMetadata (catalog, lineage, quality) and Apache Ranger/OPA (policy), with Keycloak for identity. Compute runs on Kubernetes; storage runs outside it.

## Data zones

| Zone | Contents | POC location |
| --- | --- | --- |
| Raw | Exact files as received, write-once | `s3://raw/` (object lock enabled) |
| Bronze | Parsed, typed, append-only, all versions | `lakehouse.bronze.*` Iceberg tables |
| Silver | Validated, conformed, identifiers tokenised | `lakehouse.silver.*` |
| Gold | Certified data products | `lakehouse.gold.*` |
| Archive | Cold copies | `s3://archive/` |

## In scope for the POC

- Batch path: synthetic file → Raw → Bronze → Silver → Gold → Trino → Superset.
- Streaming path: synthetic events → Kafka → Flink → Iceberg.
- Data contracts, quality rules as code, quality results stored as data.
- Catalog and lineage (OpenMetadata), SSO (Keycloak).
- GitOps deployment (Argo CD).

## Out of scope

Performance, HA/DR, HSMs, PAM, SIEM, the external-sharing zone, production security hardening, real data.
