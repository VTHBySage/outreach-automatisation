#!/bin/bash
#
# PostgreSQL Database Backup Script
#
# This script performs automated backups of the outreach-automation database.
# Schedule this script to run every 6 hours using cron:
#
# 0 */6 * * * /path/to/backup_db.sh >> /var/log/db_backup.log 2>&1
#
# Requirements:
# - pg_dump command available
# - DATABASE_URL environment variable set
# - BACKUP_DIR environment variable (optional, defaults to ./backups)
# - AWS CLI configured (optional, for S3 uploads)
#

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/outreach-automation}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
S3_BUCKET="${S3_BACKUP_BUCKET:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="outreach_automation_backup_${TIMESTAMP}.sql.gz"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARN:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Check required environment variables
if [ -z "$DATABASE_URL" ]; then
    log_error "DATABASE_URL environment variable is not set"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log_info "Starting database backup..."
log_info "Backup file: $BACKUP_FILE"

# Parse DATABASE_URL
# Format: postgresql://user:password@host:port/dbname
if [[ "$DATABASE_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
    DB_USER="${BASH_REMATCH[1]}"
    DB_PASSWORD="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
else
    log_error "Could not parse DATABASE_URL"
    exit 1
fi

# Set PGPASSWORD for pg_dump
export PGPASSWORD="$DB_PASSWORD"

# Perform backup with compression
log_info "Running pg_dump..."
pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --format=custom \
    | gzip > "$BACKUP_DIR/$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(ls -lh "$BACKUP_DIR/$BACKUP_FILE" | awk '{print $5}')
    log_info "Backup completed successfully: $BACKUP_SIZE"
else
    log_error "Backup failed!"
    exit 1
fi

# Upload to S3 if bucket is configured
if [ -n "$S3_BUCKET" ]; then
    log_info "Uploading to S3: s3://$S3_BUCKET/$BACKUP_FILE"

    if command -v aws &> /dev/null; then
        aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://$S3_BUCKET/$BACKUP_FILE"

        if [ $? -eq 0 ]; then
            log_info "S3 upload completed successfully"
        else
            log_warn "S3 upload failed - local backup still available"
        fi
    else
        log_warn "AWS CLI not found - skipping S3 upload"
    fi
fi

# Cleanup old backups (local)
log_info "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "outreach_automation_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
REMAINING_BACKUPS=$(ls -1 "$BACKUP_DIR"/*.sql.gz 2>/dev/null | wc -l)
log_info "Cleanup complete. $REMAINING_BACKUPS backup(s) remaining locally"

# Generate backup manifest
MANIFEST_FILE="$BACKUP_DIR/backup_manifest.json"
cat > "$MANIFEST_FILE" << EOF
{
    "last_backup": "$TIMESTAMP",
    "last_backup_file": "$BACKUP_FILE",
    "last_backup_size": "$BACKUP_SIZE",
    "retention_days": $RETENTION_DAYS,
    "s3_bucket": "${S3_BUCKET:-null}",
    "total_local_backups": $REMAINING_BACKUPS
}
EOF

log_info "Backup manifest updated: $MANIFEST_FILE"
log_info "Database backup completed successfully!"

# Exit with success
exit 0
