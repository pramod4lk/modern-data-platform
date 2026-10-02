# Runbook 03 — MicroCeph and S3 buckets

Automated: `make ceph` then `make buckets`.

## Install MicroCeph (on ceph-1)
```bash
sudo snap install microceph
sudo snap refresh --hold microceph
sudo microceph cluster bootstrap
lsblk                                    # data disks, e.g. /dev/vdb /dev/vdc
sudo microceph disk add /dev/vdb --wipe
sudo microceph disk add /dev/vdc --wipe
sudo ceph config set global osd_pool_default_size 1      # single node only
sudo ceph config set global mon_allow_pool_size_one true
sudo ceph config set osd osd_memory_target 805306368     # 768 MB per OSD (ceph-1 has 3 GB)
sudo microceph enable rgw --port 8080
sudo ceph -s
```

## Create an S3 user
```bash
sudo radosgw-admin user create --uid=poc --display-name="POC user"
# Note access_key and secret_key from the output — store them outside Git.
```

## Create buckets
```bash
export S3_ENDPOINT=http://ceph-1:8080
export AWS_ACCESS_KEY_ID=<access_key>
export AWS_SECRET_ACCESS_KEY=<secret_key>
./infra/storage/create-buckets.sh
```

## Make credentials available to Kubernetes
```bash
kubectl create namespace lakehouse --dry-run=client -o yaml | kubectl apply -f -
kubectl -n lakehouse create secret generic s3-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=<access_key> \
  --from-literal=AWS_SECRET_ACCESS_KEY=<secret_key>
```
Repeat for other namespaces that need S3 (`orchestration`, `streaming`).
