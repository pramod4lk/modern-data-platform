# Learning path

This lab exists to **learn every technology and concept** in the target architecture by building a small, working version of it. Each milestone teaches a set of concepts; each concept has a hands-on exercise in this repository.

Work through it in order. After each milestone, write down what surprised you in `docs/adr/` or a short note — that is how the lessons reach the real programme.

## Milestone 1 — Infrastructure foundations

| Concept | Technology | Where | Exercise |
| --- | --- | --- | --- |
| Virtualisation, bridged networking | KVM/libvirt, VMware | `infra/vms/` | Explain why bridging fails over Wi-Fi; inspect `br-poc` with `bridge link` |
| Infrastructure as Code | Ansible | `infra/ansible/` | Run `make base-os` twice; confirm the second run changes nothing (idempotency) |
| Kubernetes architecture | k3s | Runbook 02 | Identify control plane vs agents; `kubectl describe node`; drain and uncordon a worker |
| Scheduling and placement | labels, nodeSelector | `poc/role` labels | Move a pod between nodes by changing its nodeSelector |
| Object storage, erasure coding vs replication | Ceph (MicroCeph) | Runbook 03 | `ceph -s`, `ceph osd tree`, `ceph df`; explain why pool size is 1 here and 3 / EC 8+3 in production |
| Immutability (WORM) | S3 Object Lock | `infra/storage/` | Upload to `raw` with a retention period, then try to delete it |

## Milestone 2 — Lakehouse core

| Concept | Technology | Where | Exercise |
| --- | --- | --- | --- |
| Separation of storage and compute | S3 + engines | `common/config.py` | Stop Trino; data is still in Ceph; start it again |
| Open table format | Apache Iceberg | `smoke_test.py` | Browse `s3://lakehouse/` and find the data files, manifest lists and `metadata.json` |
| Catalog and REST catalog standard | Apache Polaris | `components/polaris/` | Read a table from Spark and Trino through the same catalog |
| Time travel and snapshots | Iceberg | `tests/smoke/check_trino.sh` | Query a table `FOR VERSION AS OF` an older snapshot |
| Schema evolution | Iceberg | — | `ALTER TABLE ... ADD COLUMN`; old data still reads |
| Federated SQL | Trino | `components/trino/` | Join `tpch` sample data with an Iceberg table |
| GitOps | Argo CD | `platform/bootstrap/`, `platform/apps/` | Change a value in Git, watch Argo CD show the app out of sync, then sync |

## Milestone 3 — Batch pipeline and data quality

| Concept | Technology | Where | Exercise |
| --- | --- | --- | --- |
| Data contracts | ODCS-style YAML | `data/contracts/` | Change the contract, then see `validate_structure.py` reject old files |
| Medallion architecture | Raw → Bronze → Silver → Gold | `data/pipelines/` | Trace one number from Gold back to the raw file via `submission_id` |
| Idempotency and replay | Spark + Iceberg | `raw_to_bronze.py` | Run the same submission twice; row counts do not double |
| Versioned resubmissions | Bronze keeps all versions | dbt Silver model | Submit `--version 2`; Silver shows v2, Bronze keeps v1 and v2 |
| Quality rules as code, quarantine | rules engine | `data/quality/` | `--inject-error negative_amount`; see the submission quarantined |
| SQL transformations, tests | dbt | `data/pipelines/dbt/` | Add a column to Gold and a test for it |
| Orchestration, retries, dependencies | Airflow | `data/orchestration/` | Kill a Spark driver pod mid-run; watch Airflow retry |
| Scheduling | Airflow schedules | `reference_daily.py` | Switch the DAG on; change its schedule; read the run history |

## Milestone 4 — Streaming

| Concept | Technology | Where | Exercise |
| --- | --- | --- | --- |
| Event log, partitions, consumer groups | Kafka (Strimzi, KRaft) | `components/kafka/` | Produce events; check consumer lag; replay from earliest offset |
| Schema registry | Apicurio | `components/apicurio/` | Register `payments-event.v1.avsc`; try an incompatible change |
| Event time, watermarks, late data | Flink | `payments_stream.sql` | Produce late events (`--late-ratio 0.2`); see which are accepted |
| Deduplication, exactly-once into Iceberg | Flink checkpoints | same | Produce duplicates; confirm Bronze has one row per `event_id` |
| Dead-letter queues | Kafka topics | `payments.events.v1.dlq` | Send malformed JSON; decide how it should reach the DLQ |
| Kappa vs Lambda | one path for stream and batch | — | Query streaming and batch data together in Trino |

## Milestone 5 — Serving, security and governance

| Concept | Technology | Where | Exercise |
| --- | --- | --- | --- |
| BI and dashboards as code | Superset | `data/dashboards/superset/` | Build the LCR dashboard; export it to Git |
| Identity federation, SSO, OIDC | Keycloak | `components/keycloak/` | Log in to Superset through Keycloak |
| RBAC vs ABAC, row filters, column masking | Trino rules / OPA / Ranger | `components/ranger/` | `analyst` sees masked names; `supervisor` sees only their institutions |
| Catalog, glossary, ownership, classification | OpenMetadata | `components/openmetadata/` | Register Gold with owner, tags and a glossary term |
| Lineage (table and column) | OpenLineage | Airflow, Spark, dbt | See Raw → Gold lineage for the LCR product |
| Observability | Prometheus, Grafana | `components/monitoring/` | Build a panel for Kafka lag or pipeline duration |

## Milestone 6 — Operating the platform

| Concept | Exercise |
| --- | --- |
| Failure and recovery | Power off `k3s-worker-1` during a job; observe and recover |
| Rollback | Roll a Gold table back to a previous snapshot |
| Onboarding by configuration | Onboard FI002 with `onboarding/institutions/FI002.yaml` only |
| Capacity thinking | Use `kubectl top` to find the next bottleneck and propose a fix in an ADR |
| Lab → production mapping | For each component, list what changes in production (HA, security, sizing) |

## Concepts the lab cannot show (study from the architecture document)

Two-site DR and RPO/RTO, HSM-backed key management, PAM and segregation of duties, SIEM integration, external data sharing and disclosure control, petabyte-scale sizing.
