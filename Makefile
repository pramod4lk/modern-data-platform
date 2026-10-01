# Shortcuts for the POC. Run `make help` to list targets.
ANSIBLE_INV := infra/inventory/hosts.yaml
PLAYBOOKS   := infra/ansible/playbooks

.PHONY: help vms base-os k3s ceph buckets argocd root-app generate-lcr smoke lint

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n",$$1,$$2}'

vms:             ## Create the Linux KVM VMs (run on the Linux host, not with sudo)
	./infra/vms/linux-kvm/create-poc-vms.sh

base-os:         ## Prepare OS on all VMs (updates, timezone, swap off, /etc/hosts)
	ansible-playbook -i $(ANSIBLE_INV) $(PLAYBOOKS)/base-os.yml

k3s:             ## Install k3s server and agents
	ansible-playbook -i $(ANSIBLE_INV) $(PLAYBOOKS)/k3s-server.yml
	ansible-playbook -i $(ANSIBLE_INV) $(PLAYBOOKS)/k3s-agents.yml

ceph:            ## Install MicroCeph and the S3 gateway on ceph-1
	ansible-playbook -i $(ANSIBLE_INV) $(PLAYBOOKS)/microceph.yml

buckets:         ## Create raw / lakehouse / archive buckets (needs S3 env vars)
	./infra/storage/create-buckets.sh

argocd:          ## Install Argo CD into the cluster
	helm repo add argo https://argoproj.github.io/argo-helm && helm repo update
	helm upgrade --install argocd argo/argo-cd -n argocd --create-namespace \
	  -f platform/bootstrap/argocd/values.yaml

root-app:        ## Register the app-of-apps with Argo CD
	kubectl apply -f platform/namespaces/namespaces.yaml
	kubectl apply -f platform/bootstrap/root-app.yaml

generate-lcr:    ## Generate synthetic monthly LCR files
	python data/generators/generate_lcr_files.py --period 2026-09 --institutions 5

smoke:           ## Run smoke tests
	./tests/smoke/check_s3.sh
	./tests/smoke/check_trino.sh

lint:            ## Run all pre-commit hooks
	pre-commit run --all-files
