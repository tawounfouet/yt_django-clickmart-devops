#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/clickmart/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

docker compose -f /opt/clickmart/docker-compose.yml exec -T db \
  pg_dump -U postgres clickmart | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

# Weekly rotation (Sundays → 30-day retention)
if [ "$(date +%u)" = "7" ]; then
    mkdir -p "$BACKUP_DIR/weekly"
    cp "$BACKUP_DIR/db_$TIMESTAMP.sql.gz" "$BACKUP_DIR/weekly/"
    find "$BACKUP_DIR/weekly" -name "db_*.sql.gz" -mtime +30 -delete
    echo "[$(date)] Weekly copy: db_$TIMESTAMP.sql.gz"
fi

echo "[$(date)] Backup: db_$TIMESTAMP.sql.gz"
