# ADR-0003: k3s for the local POC

- **Status:** Accepted
- **Date:** 2026-10-01

## Context
The POC is a learning lab on two laptops: a 16 GB Linux laptop and a 32 GB Windows laptop. The target platform will use a supported distribution (OpenShift or Rancher RKE2), which is too heavy for laptops.

## Options considered
1. **k3s** — lightweight, single binary, CNCF-certified Kubernetes; same Helm charts.
2. **kind / minikube** — single-host only; cannot span two laptops.
3. **kubeadm** — closer to upstream, much more setup effort.

## Decision
k3s: one server and two agents across both laptops.

## Consequences
- Helm values and manifests carry over to RKE2/OpenShift with minor changes (storage classes, security contexts, ingress).
- No HA control plane in the POC.
