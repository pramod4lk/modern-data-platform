# Runbook 01 — Network and VMs

## 1. Network
Both laptops are cabled to a gigabit switch that is cabled to the router. **Turn Wi-Fi off on both laptops.**

Find your router and DHCP range, then choose four static IPs outside the DHCP range and record them in `infra/inventory/hosts.yaml`.

### Linux host: bridge `br-poc`
```bash
ip link                                  # e.g. enp3s0
nmcli con show                           # e.g. "Wired connection 1"
sudo nmcli radio wifi off
sudo nmcli con add type bridge ifname br-poc con-name br-poc \
  ipv4.method auto ipv6.method disabled bridge.stp no
sudo nmcli con add type bridge-slave ifname enp3s0 master br-poc con-name br-poc-port
sudo nmcli con down "Wired connection 1"
sudo nmcli con up br-poc
ip addr show br-poc && ping -c 3 8.8.8.8
```

### Windows host: VMware
1. Turn Wi-Fi off.
2. Virtual Network Editor (as Administrator) → **VMnet0** → Bridged to your **Ethernet adapter** (not Automatic).

## 2. Create VMs
- Linux: `./infra/vms/linux-kvm/create-poc-vms.sh` (as your normal user).
- Windows: see `infra/vms/windows-vmware/README.md`.

## 3. Install Ubuntu Server
- Network: manual IPv4 (subnet, VM IP, gateway = router, DNS = router + 1.1.1.1).
- Storage: entire disk; set `ubuntu-lv` to max size. On `ceph-1` use only the first disk.
- Hostname = VM name; OpenSSH server enabled; no snaps.

Eject the ISO after installation:
```bash
sudo virsh domblklist k3s-server
sudo virsh change-media k3s-server sda --eject --config
```

## 4. OS preparation
Run `make base-os` (Ansible), or manually on each VM:
```bash
sudo apt update && sudo apt -y full-upgrade
sudo timedatectl set-timezone Asia/Kuala_Lumpur
sudo swapoff -a && sudo sed -i '/ swap / s/^/#/' /etc/fstab
```
and add all four hostnames to `/etc/hosts`.

## 5. Verify
```bash
for h in k3s-server k3s-worker-1 ceph-1 k3s-worker-2; do ping -c 2 $h; done
```
