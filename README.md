# data-platform-poc

A local proof of concept (POC) of the central bank's modern data platform: an open-standard **lakehouse** (Apache Iceberg on Ceph object storage), fed by **Kafka**, processed by **Spark and Flink**, orchestrated by **Airflow**, queried through **Trino**, and governed through **OpenMetadata** and **Keycloak**, all running on **Kubernetes (k3s)** across VMs on two laptops.

The POC proves **how the components fit together and how data flows** end to end. It does not test performance, high availability or production security; those are covered by the Phase 0 PoC on real servers.

> **Rules for this repository**
> - **Synthetic data only.** Never commit or load real bank, institution or customer data, even though the repository is private.
> - **No secrets in Git.** No passwords, tokens, private keys or kubeconfig files. See `platform/secrets/README.md`.

---

## Contents

- [Target design vs POC](#target-design-vs-poc)
- [Lab topology](#lab-topology)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Milestones](#milestones)
- [Component placement](#component-placement)
- [Repository structure](#repository-structure)
- [Working conventions](#working-conventions)
- [Troubleshooting](#troubleshooting)

---

## Target design vs POC

| Target platform | Local POC | Why |
| --- | --- | --- |
| OpenShift / RKE2, several clusters per site | **k3s**, one cluster across 3 VMs | Lightweight Kubernetes; the same Helm charts work |
| Ceph cluster on bare metal | **MicroCeph** (single-node Ceph) in its own VM | Same S3 API and technology as the target; stays outside Kubernetes |
| Kafka, 5+ brokers | Strimzi Kafka, 1 broker | Same operator and APIs |
| Separate Trino clusters per workload | One small Trino | Same SQL and Iceberg behaviour |
| Two data centres, HSMs, PAM, SIEM, external-sharing cluster | Not included | Cannot be meaningfully simulated on laptops |

---

## Lab topology

Two laptops (Linux and Windows) connected to a gigabit switch that is cabled to the home/office router. **Wi-Fi is turned off on both laptops**; all VMs use bridged networking and get static IPs on the router's subnet.

```
                    Router (192.168.1.1)
                           │
                     Gigabit switch
                  ┌────────┴────────┐
        Linux laptop (KVM)     Windows laptop (VMware)
        bridge: br-poc         VMnet0 bridged to Ethernet
        ├── k3s-server         └── k3s-worker-2
        ├── k3s-worker-1
        └── ceph-1
```

| VM | Host | vCPU | RAM | Disk | IP (example) | Role |
| --- | --- | --- | --- | --- | --- | --- |
| `k3s-server` | Linux (KVM) | 2 | 3 GB | 30 GB | 192.168.1.201 | k3s control plane + light services |
| `k3s-worker-1` | Linux (KVM) | 4 | 6 GB | 60 GB | 192.168.1.202 | Compute: Spark, Trino |
| `ceph-1` | Linux (KVM) | 2 | 3 GB | 20 GB OS + 2 × 40 GB data | 192.168.1.203 | MicroCeph S3 storage (not in k3s) |
| `k3s-worker-2` | Windows (VMware) | 6 | 24 GB | 150 GB | 192.168.1.204 | Services: Kafka, Flink, Airflow, Superset, OpenMetadata |

The Linux VM sizes come from `infra/vms/linux-kvm/create-poc-vms.sh`, which is sized for a 16 GB host. **With 32 GB on the Linux laptop, consider raising them** to about 6 GB (server), 14 GB (worker 1) and 6 GB (Ceph). Replace the example IPs with addresses on your router's subnet, outside its DHCP range, and keep them in sync with `infra/inventory/hosts.yaml`.

---

## Prerequisites

**Both laptops**
- Hardware virtualisation (Intel VT-x / AMD-V) enabled in BIOS/UEFI.
- Wired Ethernet to the switch; Wi-Fi off; sleep disabled on AC power; lid-close action set to "do nothing".
- Git.

**Linux laptop**
- KVM and libvirt:
  ```bash
  sudo apt install qemu-kvm libvirt-daemon-system virtinst virt-manager bridge-utils
  sudo systemctl enable --now libvirtd
  ```
- Ubuntu Server ISO in `~/Downloads/` (the script expects `ubuntu-26.04.1-live-server-amd64.iso`; edit `ISO_NAME` in the script if yours differs).
- Network bridge `br-poc` on the Ethernet port (see Quick start, step 1).

**Windows laptop**
- VMware Workstation Pro, with **VMnet0** bridged to the Ethernet adapter (not "Automatic").
- Docker Desktop **quit** while the POC runs, or its WSL2 memory capped in `%USERPROFILE%\.wslconfig`:
  ```ini
  [wsl2]
  memory=4GB
  ```
- Docker is used only to build the custom images in `images/`.

---

## Quick start

Detailed steps are in [`docs/runbooks/`](docs/runbooks/).

### 1. Network (Linux host)

```bash
ip link                        # find the Ethernet port, e.g. enp3s0
sudo nmcli radio wifi off
sudo nmcli con add type bridge ifname br-poc con-name br-poc \
  ipv4.method auto ipv6.method disabled bridge.stp no
sudo nmcli con add type bridge-slave ifname enp3s0 master br-poc con-name br-poc-port
sudo nmcli con down "Wired connection 1"
sudo nmcli con up br-poc
```

### 2. Create the Linux VMs

Run as your **normal user, not with sudo**; the script calls `sudo` itself.

```bash
./infra/vms/linux-kvm/create-poc-vms.sh
```

The script checks libvirt and the `br-poc` bridge, copies the ISO into `/var/lib/libvirt/images`, enables KSM (memory-page sharing between VMs), and creates `k3s-server`, `k3s-worker-1` and `ceph-1`. It skips any VM that already exists, so it is safe to re-run.

Create `k3s-worker-2` in VMware on the Windows laptop by hand; see [`infra/vms/windows-vmware/README.md`](infra/vms/windows-vmware/README.md).

### 3. Install Ubuntu in each VM

Open each VM's console (virt-manager on Linux, VMware on Windows) and install Ubuntu Server with:

- **Network:** manual IPv4, the VM's static IP, gateway and DNS = your router (plus `1.1.1.1`).
- **Storage:** entire disk; set `ubuntu-lv` to the maximum size. On `ceph-1`, install only on the first (20 GB) disk and leave the data disks untouched.
- **Hostname:** the VM name. **OpenSSH server:** enabled. **Snaps:** none.

After installation, eject the ISO (check the device name first):

```bash
sudo virsh domblklist k3s-server
sudo virsh change-media k3s-server sda --eject --config
# repeat for k3s-worker-1 and ceph-1
```

### 4. Prepare the OS (all four VMs)

```bash
sudo apt update && sudo apt -y full-upgrade
sudo timedatectl set-timezone Asia/Kuala_Lumpur
sudo swapoff -a && sudo sed -i '/ swap / s/^/#/' /etc/fstab
sudo tee -a /etc/hosts <<'EOF'
192.168.1.201 k3s-server
192.168.1.202 k3s-worker-1
192.168.1.203 ceph-1
192.168.1.204 k3s-worker-2
EOF
sudo reboot
```

Check each VM can reach the others and the internet:

```bash
for h in k3s-server k3s-worker-1 ceph-1 k3s-worker-2; do ping -c 2 $h; done
ping -c 2 google.com
```

### 5. Install k3s

On `k3s-server`:

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --node-ip 192.168.1.201 --tls-san 192.168.1.201 \
  --write-kubeconfig-mode 644" sh -
sudo cat /var/lib/rancher/k3s/server/node-token     # copy the token
```

On each worker (use its own IP for `--node-ip`):

```bash
curl -sfL https://get.k3s.io | K3S_URL=https://192.168.1.201:6443 \
  K3S_TOKEN=<token> INSTALL_K3S_EXEC="agent --node-ip 192.168.1.202" sh -
```

Back on `k3s-server`:

```bash
kubectl get nodes -o wide          # expect 3 nodes, STATUS Ready
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
kubectl label node k3s-worker-1 poc/role=compute
kubectl label node k3s-worker-2 poc/role=services
```

### 6. Storage (MicroCeph)

See [`docs/runbooks/03-microceph-s3.md`](docs/runbooks/03-microceph-s3.md). After Ceph is deployed, cap OSD memory to fit the small VM:

```bash
sudo ceph config set osd osd_memory_target 1073741824
```

Then create the `raw`, `lakehouse` and `archive` buckets defined in `infra/storage/buckets.yaml` (`make buckets`).

### 7. Platform components (GitOps)

1. Create the Secrets listed in [`platform/secrets/README.md`](platform/secrets/README.md).
2. Set your Git URL in `platform/bootstrap/root-app.yaml`, `platform/apps/*.yaml` and `platform/components/airflow/values.yaml`.
3. `make argocd` then `make root-app`.
4. In the Argo CD UI, sync components milestone by milestone (sync waves order them).

Chart versions are set to the latest (`"*"`) and some chart keys change between releases: run `helm show values` for each chart and pin `targetRevision` once a component works.

---

## Milestones

Each milestone must work before starting the next. Details and success criteria: [`docs/milestones.md`](docs/milestones.md).

- [ ] **M1 — Foundation:** VMs, k3s cluster (3 nodes Ready), MicroCeph with S3 buckets.
- [ ] **M2 — Lakehouse core:** PostgreSQL, Polaris (Iceberg REST catalog), Trino, Spark. One Iceberg table written by Spark and queried by Trino.
- [ ] **M3 — Batch pipeline:** a synthetic monthly liquidity return from one institution flows Raw → Bronze → Silver → Gold, orchestrated by Airflow, with Great Expectations quality checks.
- [ ] **M4 — Streaming:** Strimzi Kafka + Flink (or Spark Structured Streaming) writing payment events into an Iceberg table.
- [ ] **M5 — Serving and governance:** Superset dashboards on Trino, Keycloak SSO, OpenMetadata catalog and lineage; stretch goal: Ranger column masking in Trino.
- [ ] **M6 — Proof tests:** corrected resubmission creates a new version; time-travel rollback; pod failure recovery; onboarding a second institution by configuration only.

**The POC succeeds when** one synthetic institution's file and one event stream reach a Gold table and a dashboard, with lineage, quality results and time travel all visible.

---

## Component placement

| Node | Components |
| --- | --- |
| `k3s-server` | k3s control plane, PostgreSQL, Keycloak, Polaris, Apicurio schema registry |
| `k3s-worker-1` (`poc/role=compute`) | Spark jobs, Trino, dbt, Great Expectations |
| `k3s-worker-2` (`poc/role=services`) | Kafka (Strimzi), Flink, Airflow, Superset, OpenMetadata, NiFi (optional) |
| `ceph-1` (outside k3s) | MicroCeph S3 storage |

---

## Repository structure

```
data-platform-poc/
├── README.md                          # This file
├── .gitignore                         # kubeconfig, .env, keys, secrets, local data, ISOs
├── .editorconfig
├── .pre-commit-config.yaml            # yamllint, ruff, shellcheck, gitleaks
├── Makefile                           # make vms | base-os | k3s | ceph | buckets | argocd | smoke ...
│
├── .github/workflows/
│   └── lint.yml                       # pre-commit, kubeconform, dbt parse, Python syntax
│
├── docs/
│   ├── architecture.md                # Link to the architecture document + POC scope
│   ├── milestones.md                  # 6 milestones with checklists and success criteria
│   ├── adr/                           # Architecture Decision Records
│   │   ├── 0000-template.md
│   │   ├── 0001-iceberg-table-format.md
│   │   ├── 0002-polaris-catalog.md
│   │   └── 0003-k3s-for-poc.md
│   └── runbooks/
│       ├── 01-network-and-vms.md
│       ├── 02-k3s-install.md
│       ├── 03-microceph-s3.md
│       └── troubleshooting.md
│
├── infra/                             # Everything outside Kubernetes
│   ├── inventory/
│   │   └── hosts.yaml                 # VM names, IPs, roles (also the Ansible inventory)
│   ├── vms/
│   │   ├── linux-kvm/
│   │   │   └── create-poc-vms.sh      # Creates k3s-server, k3s-worker-1, ceph-1
│   │   └── windows-vmware/
│   │       └── README.md              # Manual steps for k3s-worker-2
│   ├── ansible/
│   │   ├── ansible.cfg
│   │   ├── playbooks/
│   │   │   ├── base-os.yml            # updates, timezone, swap off, /etc/hosts, sysctl
│   │   │   ├── k3s-server.yml
│   │   │   ├── k3s-agents.yml         # join workers + apply poc/role labels
│   │   │   └── microceph.yml          # single-node Ceph + S3 gateway
│   │   └── roles/                     # (empty for now)
│   └── storage/
│       ├── buckets.yaml               # raw, lakehouse, archive + object lock / versioning
│       └── create-buckets.sh
│
├── platform/                          # Everything deployed on Kubernetes (GitOps)
│   ├── bootstrap/
│   │   ├── argocd/values.yaml         # Small Argo CD install
│   │   └── root-app.yaml              # App of apps -> platform/apps/
│   ├── namespaces/namespaces.yaml     # data-system, identity, lakehouse, streaming, orchestration, bi, governance, monitoring
│   ├── apps/                          # One Argo CD Application per component (manual sync)
│   │   ├── monitoring.yaml  cnpg-operator.yaml  postgresql.yaml  keycloak.yaml
│   │   ├── polaris.yaml  apicurio.yaml  trino.yaml  spark-operator.yaml
│   │   ├── strimzi-operator.yaml  kafka.yaml  flink-operator.yaml
│   │   └── airflow.yaml  superset.yaml  openmetadata-deps.yaml  openmetadata.yaml
│   ├── components/                    # Helm values and manifests per component
│   │   ├── postgresql/                # CloudNativePG cluster, databases, ledger-schema.sql
│   │   ├── keycloak/                  # values.yaml, realm-poc.json
│   │   ├── polaris/                   # values.yaml, create-catalog.json
│   │   ├── apicurio/                  # Deployment + Service
│   │   ├── trino/                     # values.yaml, catalogs/iceberg.properties
│   │   ├── spark-operator/            # values.yaml, example SparkApplication
│   │   ├── kafka/                     # operator values, KRaft cluster, topics/
│   │   ├── flink-operator/
│   │   ├── airflow/
│   │   ├── superset/
│   │   ├── openmetadata/              # dependencies (OpenSearch) + server values
│   │   ├── ranger/                    # Stretch goal: README + Trino rules example
│   │   └── monitoring/                # kube-prometheus-stack values
│   └── secrets/README.md              # Which Secrets to create by hand; no values in Git
│
├── images/                            # Custom container images (built with Docker)
│   ├── spark/                         # Spark + Iceberg + S3 + POC pipelines
│   └── airflow/                       # Airflow + providers + dbt
│
├── data/
│   ├── reference/                     # Synthetic institutions FI001-FI045 + code lists
│   ├── contracts/                     # Data contracts (ODCS style) + schemas/
│   │   ├── lcr-monthly.v1.yaml
│   │   ├── payments-events.v1.yaml
│   │   └── schemas/                   # JSON Schema, Avro
│   ├── generators/
│   │   ├── generate_lcr_files.py      # Synthetic LCR files + manifests (with error injection)
│   │   ├── submit_file.py             # Ingestion-gateway stand-in: Raw + ledger + receipt
│   │   └── produce_payment_events.py  # Synthetic Kafka events (late + duplicate events)
│   ├── pipelines/
│   │   ├── spark/
│   │   │   ├── common/                # Spark/S3 config, quality engine, ledger updates
│   │   │   ├── validate_structure.py  # Raw: contract + manifest checks
│   │   │   ├── raw_to_bronze.py       # Raw -> Bronze (idempotent) + Bronze quality rules
│   │   │   ├── load_reference.py      # Reference CSVs -> lakehouse.reference.*
│   │   │   └── smoke_test.py          # Milestone 2: Spark writes Iceberg, Trino reads
│   │   ├── flink/payments_stream/     # Kafka -> dedup -> Iceberg Bronze + 1-minute stats
│   │   └── dbt/                       # Silver (current version) and Gold (LCR) models + tests
│   ├── quality/                       # Rules as code per contract (results -> ops.dq_results)
│   ├── orchestration/airflow/dags/
│   │   ├── lcr_monthly_pipeline.py    # validate -> bronze -> dbt -> publish
│   │   └── spark-apps/                # SparkApplication templates rendered per run
│   └── dashboards/superset/           # Exported dashboards (README explains how)
│
├── onboarding/institutions/           # A new institution = a new YAML file
│   ├── _template.yaml
│   ├── FI001.yaml
│   └── FI002.yaml
│
└── tests/
    ├── smoke/                         # check_s3.sh, check_trino.sh
    └── e2e/                           # test_lcr_e2e.sh: generate -> submit -> DAG -> Gold
```

### How the folders map to the architecture

| Folder | Architecture concept |
| --- | --- |
| `infra/` | Infrastructure as Code (Ansible here; Terraform/OpenTofu in the real build) |
| `platform/` + Argo CD | GitOps: the cluster always matches what is in Git |
| `data/contracts/` | Data contracts: no pipeline is built before its contract exists |
| `data/pipelines/` + `data/quality/` | Raw → Bronze → Silver → Gold with quality gates |
| `onboarding/institutions/` | A new institution is a new YAML file, not new code |
| `docs/adr/` | Architecture Board decision records |

---

## Working conventions

- **Branches:** `main` is always deployable. Work on short-lived branches (`feat/trino-iceberg`, `fix/ceph-bucket-policy`) and merge by pull request.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/), e.g. `feat(platform): add Trino Iceberg catalog`, `docs(runbook): k3s install`.
- **Decisions:** one ADR in `docs/adr/` per significant decision (context, options, decision, consequences).
- **Secrets:** created in the cluster via Sealed Secrets or SOPS; only encrypted or template files are committed.
- **Pre-commit:** run `pre-commit install` once; hooks lint YAML/Python and block accidental secrets.
- **Scripts from Windows:** keep the executable bit, e.g. `git update-index --chmod=+x infra/vms/linux-kvm/create-poc-vms.sh`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Bridge 'br-poc' not found` from the VM script | Bridge not created or not up | Re-run Quick start step 1; check `ip addr show br-poc` |
| `Cannot reach libvirt` | libvirtd not running | `sudo systemctl enable --now libvirtd` |
| VMs get no network on the Linux host | Docker/firewall filtering bridged traffic | `sudo sysctl -w net.bridge.bridge-nf-call-iptables=0` |
| Intermittent connectivity | Wi-Fi and Ethernet both active on a laptop | Turn Wi-Fi off or prefer Ethernet |
| Worker never becomes `Ready` | Ports blocked or wrong `--node-ip` | Allow 6443/tcp, 10250/tcp, 8472/udp between VMs; check the IP |
| Windows VM slow or host out of memory | Docker Desktop/WSL2 using RAM | Quit Docker Desktop or cap WSL2 memory |
| Nodes drop out overnight | Laptop went to sleep | Disable sleep on AC power; lid close = do nothing |

---

## Status

Internal proof of concept for architecture learning. Not for production use and not a procurement specification.
