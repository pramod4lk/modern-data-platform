# k3s-worker-2 on Windows (VMware Workstation)

## Before you start
- Wi-Fi off; laptop cabled to the switch.
- Virtual Network Editor (as Administrator): **VMnet0 → Bridged → your Ethernet adapter** (not Automatic).
- Quit Docker Desktop, or cap WSL2 memory in `%USERPROFILE%\.wslconfig`:
  ```ini
  [wsl2]
  memory=4GB
  ```
- Power settings: no sleep on AC; lid close = do nothing.

## Create the VM
1. File → New Virtual Machine → **Typical** → installer disc image: Ubuntu Server ISO (same version as the Linux VMs).
2. Name: `k3s-worker-2`. Disk: **150 GB**, single file.
3. **Customize Hardware:**
   - Memory: **24 GB**
   - Processors: **6** (keep at least 2 physical cores free for Windows)
   - Network Adapter: **Custom → VMnet0 (Bridged)**
   - Remove: sound card, printer, USB controller (not needed)
4. Finish and power on.

## Install Ubuntu
- Network: manual IPv4 with the IP from `infra/inventory/hosts.yaml` (e.g. 192.168.1.204), gateway and DNS = router.
- Storage: entire disk; set `ubuntu-lv` to max.
- Hostname: `k3s-worker-2`; user: `poc`; OpenSSH server: on; snaps: none.

After installation: VM → Settings → CD/DVD → uncheck **Connect at power on**.

## Verify
```bash
ping -c 2 k3s-server && ping -c 2 google.com
```
Then join the cluster (Runbook 02).
