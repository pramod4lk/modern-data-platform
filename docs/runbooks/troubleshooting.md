# Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Bridge 'br-poc' not found` | Bridge not created/up | Runbook 01 step 1; `ip addr show br-poc` |
| `Cannot reach libvirt` | libvirtd stopped | `sudo systemctl enable --now libvirtd` |
| VMs have no network on Linux host | Docker/firewall filters bridged traffic | `sudo sysctl -w net.bridge.bridge-nf-call-iptables=0` |
| Intermittent connectivity | Wi-Fi and Ethernet both active | Turn Wi-Fi off |
| Worker not `Ready` | Ports blocked / wrong `--node-ip` | Allow 6443/tcp, 10250/tcp, 8472/udp; check IP |
| Pods `Pending` | Not enough memory on the target node | `kubectl describe pod`; reduce requests or stop unused components |
| Ceph `HEALTH_WARN` pool size 1 | Expected on single node | Ignore in POC |
| Trino cannot read Iceberg | Wrong S3 endpoint / path-style access | Check `iceberg.properties`: endpoint and `s3.path-style-access=true` |
| Windows VM slow | Docker Desktop/WSL2 using RAM | Quit Docker Desktop or cap WSL2 memory |
| Nodes drop out overnight | Laptop sleep | Disable sleep on AC; lid close = do nothing |
