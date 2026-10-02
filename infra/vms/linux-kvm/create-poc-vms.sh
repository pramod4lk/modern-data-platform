#!/usr/bin/env bash
# Creates the k3s + Ceph POC VMs, sized for a 16 GB RAM laptop.
# Run as your normal user (NOT with sudo) - the script calls sudo where needed.
set -euo pipefail

ISO_NAME="ubuntu-26.04.1-live-server-amd64.iso"
SRC_ISO="$HOME/Downloads/$ISO_NAME"
IMG_DIR="/var/lib/libvirt/images"
ISO="$IMG_DIR/$ISO_NAME"
BRIDGE="br-poc"
DISK_OPTS="format=qcow2,bus=virtio,discard=unmap"

if [[ $EUID -eq 0 ]]; then
  echo "Run this as your normal user, not with sudo (so ~/Downloads resolves correctly)."
  exit 1
fi

# --- Pre-flight checks -------------------------------------------------------
if ! sudo virsh -c qemu:///system list >/dev/null 2>&1; then
  echo "Cannot reach libvirt. Start it with: sudo systemctl enable --now libvirtd"
  exit 1
fi

if ! ip link show "$BRIDGE" >/dev/null 2>&1; then
  echo "Bridge '$BRIDGE' not found. Create it before running this script."
  exit 1
fi

# --- ISO: copy from Downloads into libvirt's directory -----------------------
# (The VMs run as the libvirt-qemu user, which usually can't read your home folder.)
if [[ ! -f "$ISO" ]]; then
  if [[ ! -f "$SRC_ISO" ]]; then
    echo "ISO not found at $SRC_ISO"
    exit 1
  fi
  echo "Copying ISO to $IMG_DIR ..."
  sudo cp "$SRC_ISO" "$ISO"
fi

# --- OS variant: use ubuntu26.04 if this host knows it, else fall back ---------
if virt-install --osinfo list 2>/dev/null | grep -qw "ubuntu26.04" \
   || osinfo-query os 2>/dev/null | grep -qw "ubuntu26.04"; then
  OSV="ubuntu26.04"
else
  OSV="ubuntu24.04"
  echo "Note: osinfo-db doesn't know ubuntu26.04 yet; using ubuntu24.04 defaults (works fine)."
fi

# --- Host tweak: merge identical memory pages across the VMs ------------------
echo 1 | sudo tee /sys/kernel/mm/ksm/run >/dev/null

# --- VM creation --------------------------------------------------------------
create_vm() {
  local name=$1 vcpus=$2 mem=$3
  shift 3
  if sudo virsh dominfo "$name" >/dev/null 2>&1; then
    echo "VM '$name' already exists - skipping."
    return
  fi
  echo "Creating $name ($vcpus vCPU, $((mem / 1024)) GB RAM) ..."
  sudo virt-install --name "$name" --vcpus "$vcpus" --memory "$mem" \
    --cpu host-passthrough \
    "$@" \
    --cdrom "$ISO" \
    --network bridge="$BRIDGE",model=virtio \
    --os-variant "$OSV" --graphics spice --noautoconsole
}

create_vm k3s-server   2 3072 --disk size=30,$DISK_OPTS
create_vm k3s-worker-1 4 6144 --disk size=60,$DISK_OPTS
create_vm ceph-1       2 3072 \
  --disk size=20,$DISK_OPTS \
  --disk size=40,$DISK_OPTS \
  --disk size=40,$DISK_OPTS

cat <<EOF

Done. Open virt-manager and complete the Ubuntu installer in each VM.

After all three installs finish, eject the ISO (check the device name first):
  sudo virsh domblklist k3s-server
  sudo virsh change-media k3s-server sda --eject --config
  (repeat for k3s-worker-1 and ceph-1)

After deploying Ceph, cap OSD memory at 768 MB (ceph-1 has only 3 GB):
  ceph config set osd osd_memory_target 805306368
EOF
