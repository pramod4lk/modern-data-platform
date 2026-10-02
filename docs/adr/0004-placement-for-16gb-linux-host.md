# ADR-0004: Component placement for a 16 GB Linux host

- **Status:** Accepted
- **Date:** 2026-10-02

## Context
The Linux laptop has 16 GB of RAM, not 32 GB. After ~4 GB for the host, its three VMs get 12 GB (`k3s-server` 3, `k3s-worker-1` 6, `ceph-1` 3). The Windows laptop (32 GB) runs `k3s-worker-2` with 24 GB. The lab's goal is to learn the whole stack, so every component must still be deployable.

## Options considered
1. **Keep the original placement** (Trino and Keycloak on Linux VMs) — does not fit; Spark and Trino would compete for 6 GB.
2. **Drop components** (e.g. OpenMetadata, Flink) — saves memory but defeats the learning goal.
3. **Rebalance and use run profiles** — Linux VMs keep only what must be there; the Windows VM carries services; components not needed for the current milestone are paused.

## Decision
Option 3:
- `k3s-server`: control plane, PostgreSQL, Polaris.
- `k3s-worker-1`: Spark only (one job at a time: driver 1 GB, executor 1.2 GB).
- `ceph-1`: Ceph with `osd_memory_target` 768 MB.
- `k3s-worker-2`: Trino (single node), Keycloak, Kafka, Flink, Airflow, Superset, OpenMetadata, Apicurio, Argo CD, monitoring.
- Run profiles (`docs/memory-budget.md`) and `make pause` / `make resume` control what runs.

## Consequences
- Most service-to-storage traffic crosses the switch (Trino on Windows reads Ceph on Linux); acceptable on gigabit Ethernet for lab volumes.
- Trino runs coordinator and worker in one pod: the coordinator/worker split is learned from the configuration and docs rather than observed.
- Losing the Windows laptop takes most services down; the lab is not meant to be highly available.
