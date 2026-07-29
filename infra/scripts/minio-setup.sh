#!/bin/sh
# Create the static/media bucket for ClickMart on MinIO
# Run once after MinIO starts

set -e

MC_ALIAS="clickmart"
MC_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
MC_USER="${MINIO_ROOT_USER:-minioadmin}"
MC_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET="${AWS_STORAGE_BUCKET_NAME:-clickmart}"

echo "=== MinIO Setup ==="
echo "Endpoint: $MC_ENDPOINT"
echo "Bucket:   $BUCKET"

# Configure mc client
mc alias set $MC_ALIAS $MC_ENDPOINT $MC_USER $MC_PASSWORD

# Create bucket if not exists
if mc ls $MC_ALIAS/$BUCKET >/dev/null 2>&1; then
    echo "Bucket $BUCKET already exists"
else
    mc mb $MC_ALIAS/$BUCKET
    echo "Bucket $BUCKET created"
fi

# Set public read policy
mc anonymous set public $MC_ALIAS/$BUCKET
echo "✅ MinIO bucket ready"
