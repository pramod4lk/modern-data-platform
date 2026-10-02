# Memory budget and run profiles

The lab runs on a **16 GB Linux laptop** and a **32 GB Windows laptop**. Every component has a memory limit, and components are placed so that the small Linux VMs carry only what they must.

## Hosts

| Host | RAM | Kept for the host OS | Given to VMs |
| --- | --- | --- | --- |
| Linux laptop | 16 GB | ~4 GB | 12 GB: `k3s-server` 3 + `k3s-worker-1` 6 + `ceph-1` 3 |
| Windows laptop | 32 GB | ~8 GB (quit Docker Desktop) | 24 GB: `k3s-worker-2` |

KSM (enabled by `create-poc-vms.sh`) lets the three Linux VMs share identical memory pages, which usually frees a few hundred MB.

## Per-node budget (memory limits)

### `k3s-server` — 3 GB
| Component | Limit |
| --- | --- |
| Ubuntu + k3s server (API, scheduler, SQLite/etcd) | ~0.9 GB |
| CloudNativePG operator | 0.25 GB |
| PostgreSQL (shared) | 0.5 GB |
| Polaris catalog | 0.64 GB |
| **Total** | **~2.3 GB** |

### `k3s-worker-1` (`poc/role=compute`) — 6 GB
| Component | Limit |
| --- | --- |
| Ubuntu + k3s agent | ~0.7 GB |
| Spark Operator (controller + webhook) | ~0.6 GB |
| One Spark job: driver 1 GB + executor 1.2 GB + overhead | ~3.0 GB |
| **Total** | **~4.3 GB** — one Spark job at a time |

### `ceph-1` — 3 GB (the tightest VM)
| Component | Memory |
| --- | --- |
| Ubuntu | ~0.4 GB |
| Ceph monitor + manager | ~0.6 GB |
| 2 OSDs × `osd_memory_target` 768 MB | ~1.6 GB |
| RADOS Gateway (S3) | ~0.3 GB |
| **Total** | **~2.9 GB** |

If an OSD is killed for lack of memory (`dmesg | grep -i oom`), lower the target further: `sudo ceph config set osd osd_memory_target 671088640` (640 MB).

### `k3s-worker-2` (`poc/role=services`) — 24 GB
| Component | Limit |
| --- | --- |
| Ubuntu + k3s agent | ~1.0 GB |
| Argo CD | ~1.8 GB |
| Keycloak | 0.75 GB |
| Apicurio Registry | 0.5 GB |
| Trino (single node) | 2.5 GB |
| Strimzi operator + Kafka | 2.0 GB |
| Flink operator + payments job | 3.0 GB |
| Airflow (scheduler, API server, triggerer, DAG processor, task pods) | ~3.5 GB |
| Superset (web, worker, Redis) | ~2.0 GB |
| OpenMetadata + OpenSearch | ~3.3 GB |
| Monitoring (Prometheus, Grafana, exporters) | ~1.8 GB |
| **Total if everything runs** | **~22 GB** |

Everything *can* run at once, but with little headroom. Use run profiles instead.

## Run profiles

Run only what the current exercise needs. All Argo CD child apps use manual sync, so scaling a component down is not reverted.

| Profile | Use for | Running | Paused |
| --- | --- | --- | --- |
| **core** | Milestones 1–2 | PostgreSQL, Polaris, Trino, Spark Operator, Argo CD, Keycloak, Apicurio | everything else |
| **batch** | Milestone 3 | core + Airflow | streaming, bi, governance |
| **streaming** | Milestone 4 | core + Kafka + Flink | bi, governance |
| **serve-govern** | Milestone 5 | core + Airflow + Superset + OpenMetadata | streaming |
| **observe** | Any time | + monitoring | — |
| **full** | Milestone 6 demo | everything | — |

Pause and resume a namespace:

```bash
make pause NS=governance      # scale all Deployments/StatefulSets to 0
make resume NS=governance     # scale them back to 1
```

Supported for `bi`, `governance`, `orchestration` and `monitoring`. For `streaming`, see the note in the Makefile (Strimzi must have reconciliation paused first).

## Watching memory

```bash
kubectl top nodes                  # needs metrics-server (bundled with k3s)
kubectl top pods -A --sort-by=memory | head -20
kubectl get events -A --field-selector reason=OOMKilling
```
