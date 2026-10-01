#!/usr/bin/env bash
# Creates the buckets listed in buckets.yaml on the Ceph RADOS Gateway.
# Requires: aws CLI (v2) and python3 with PyYAML.
# Usage:
#   export S3_ENDPOINT=http://ceph-1:8080
#   export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
#   ./infra/storage/create-buckets.sh
set -euo pipefail

: "${S3_ENDPOINT:?Set S3_ENDPOINT, e.g. http://ceph-1:8080}"
: "${AWS_ACCESS_KEY_ID:?Set AWS_ACCESS_KEY_ID}"
: "${AWS_SECRET_ACCESS_KEY:?Set AWS_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

HERE="$(cd "$(dirname "$0")" && pwd)"
S3="aws --endpoint-url $S3_ENDPOINT"

python3 - "$HERE/buckets.yaml" <<'PY' | while IFS='|' read -r name lock versioning; do
import sys, yaml
for b in yaml.safe_load(open(sys.argv[1]))["buckets"]:
    print(f"{b['name']}|{str(b.get('object_lock', False)).lower()}|{str(b.get('versioning', False)).lower()}")
PY
  if $S3 s3api head-bucket --bucket "$name" >/dev/null 2>&1; then
    echo "Bucket '$name' already exists - skipping."
    continue
  fi
  echo "Creating bucket '$name' (object lock: $lock) ..."
  if [[ "$lock" == "true" ]]; then
    $S3 s3api create-bucket --bucket "$name" --object-lock-enabled-for-bucket
  else
    $S3 s3api create-bucket --bucket "$name"
  fi
  if [[ "$versioning" == "true" ]]; then
    $S3 s3api put-bucket-versioning --bucket "$name" --versioning-configuration Status=Enabled
  fi
done

echo "Buckets now present:"
$S3 s3 ls
