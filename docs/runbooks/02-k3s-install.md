# Runbook 02 — k3s install

Automated: `make k3s`. Manual steps below.

## Server (k3s-server)
```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --node-ip <SERVER_IP> --tls-san <SERVER_IP> \
  --write-kubeconfig-mode 644" sh -
sudo cat /var/lib/rancher/k3s/server/node-token
```

## Agents (k3s-worker-1, k3s-worker-2)
```bash
curl -sfL https://get.k3s.io | K3S_URL=https://<SERVER_IP>:6443 \
  K3S_TOKEN=<token> INSTALL_K3S_EXEC="agent --node-ip <THIS_NODE_IP>" sh -
```

## Verify and label
```bash
kubectl get nodes -o wide
kubectl label node k3s-worker-1 poc/role=compute
kubectl label node k3s-worker-2 poc/role=services
```

## Helm
```bash
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Using kubectl from your laptop (optional)
Copy `/etc/rancher/k3s/k3s.yaml` to your laptop as `~/.kube/config`, replace `127.0.0.1` with the server IP. **Never commit this file.**
