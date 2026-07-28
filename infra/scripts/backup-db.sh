#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/clickmart/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

docker compose -f /opt/clickmart/docker-compose.yml exec -T db \
  pg_dump -U postgres clickmart | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

echo "[$(date)] Backup: db_$TIMESTAMP.sql.gz"
