#!/usr/bin/env bash
# Smoke test: Ceph S3 reachable, buckets present, raw has object lock, read/write works on lakehouse.
set -euo pipefail
: "${S3_ENDPOINT:?Set S3_ENDPOINT, e.g. http://192.168.1.203:8080}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
S3="aws --endpoint-url $S3_ENDPOINT"

for b in raw lakehouse archive; do
  $S3 s3api head-bucket --bucket "$b" && echo "OK   bucket $b exists"
done

$S3 s3api get-object-lock-configuration --bucket raw >/dev/null \
  && echo "OK   object lock enabled on raw" \
  || { echo "FAIL object lock not enabled on raw"; exit 1; }

key="smoke/$(date +%s).txt"
echo "smoke test" | $S3 s3 cp - "s3://lakehouse/$key"
$S3 s3 cp "s3://lakehouse/$key" - | grep -q "smoke test" && echo "OK   write/read lakehouse"
$S3 s3 rm "s3://lakehouse/$key" >/dev/null
