#!/bin/bash

# PostgreSQL Backup Script for Mental Health PMS
# HIPAA-compliant encrypted backup with WAL archiving
# Usage: ./pg_backup.sh [environment]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/pms/backup.log"
BACKUP_DIR="/var/backups/pms"
S3_BUCKET="${BACKUP_S3_BUCKET:-pms-backups}"
ENVIRONMENT="${1:-production}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
ENCRYPTION_KEY_ID="${BACKUP_ENCRYPTION_KEY_ID}"

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-pmsdb}"
DB_USER="${DB_USER:-pms_user}"
PGPASSWORD="${DB_PASSWORD}"
export PGPASSWORD

# Logging function
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites for backup"
    
    # Check required tools
    command -v pg_basebackup >/dev/null 2>&1 || error_exit "pg_basebackup not found"
    command -v aws >/dev/null 2>&1 || error_exit "AWS CLI not found"
    command -v gpg >/dev/null 2>&1 || error_exit "GPG not found"
    
    # Check database connectivity
    pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" || error_exit "Database not accessible"
    
    # Check required environment variables
    [[ -n "${BACKUP_ENCRYPTION_KEY_ID:-}" ]] || error_exit "BACKUP_ENCRYPTION_KEY_ID not set"
    [[ -n "${DB_PASSWORD:-}" ]] || error_exit "DB_PASSWORD not set"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    log "INFO" "Prerequisites check passed"
}

# Create base backup
create_base_backup() {
    local backup_name="pms_backup_${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log "INFO" "Starting base backup: $backup_name"
    
    # Create base backup with WAL files
    pg_basebackup \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -D "$backup_path" \
        -Ft \
        -z \
        -P \
        -W \
        --wal-method=stream \
        --checkpoint=fast \
        --label="PMS_Backup_$(date +%Y%m%d_%H%M%S)" || error_exit "Base backup failed"
    
    log "INFO" "Base backup completed: $backup_path"
    echo "$backup_path"
}

# Encrypt backup
encrypt_backup() {
    local backup_path="$1"
    local encrypted_path="${backup_path}.gpg"
    
    log "INFO" "Encrypting backup: $(basename "$backup_path")"
    
    # Encrypt using GPG with the specified key
    tar -czf - -C "$(dirname "$backup_path")" "$(basename "$backup_path")" | \
        gpg --trust-model always --encrypt --recipient "$BACKUP_ENCRYPTION_KEY_ID" \
        --output "$encrypted_path" || error_exit "Backup encryption failed"
    
    # Remove unencrypted backup
    rm -rf "$backup_path"
    
    log "INFO" "Backup encrypted: $encrypted_path"
    echo "$encrypted_path"
}

# Upload to S3
upload_to_s3() {
    local encrypted_backup="$1"
    local s3_key="backups/${ENVIRONMENT}/$(basename "$encrypted_backup")"
    
    log "INFO" "Uploading backup to S3: s3://$S3_BUCKET/$s3_key"
    
    aws s3 cp "$encrypted_backup" "s3://$S3_BUCKET/$s3_key" \
        --server-side-encryption AES256 \
        --metadata "environment=$ENVIRONMENT,backup-type=base,created=$(date -u +%Y-%m-%dT%H:%M:%SZ)" || \
        error_exit "S3 upload failed"
    
    log "INFO" "Backup uploaded successfully"
    echo "s3://$S3_BUCKET/$s3_key"
}

# Verify backup integrity
verify_backup() {
    local s3_path="$1"
    
    log "INFO" "Verifying backup integrity: $s3_path"
    
    # Download and verify the backup can be decrypted
    local temp_file="/tmp/backup_verify_$(date +%s).gpg"
    aws s3 cp "$s3_path" "$temp_file" || error_exit "Failed to download backup for verification"
    
    # Test decryption (without extracting)
    gpg --quiet --decrypt "$temp_file" | head -c 1024 >/dev/null || error_exit "Backup verification failed - cannot decrypt"
    
    # Cleanup
    rm -f "$temp_file"
    
    log "INFO" "Backup verification passed"
}

# Cleanup old backups
cleanup_old_backups() {
    log "INFO" "Cleaning up backups older than $RETENTION_DAYS days"
    
    # Local cleanup
    find "$BACKUP_DIR" -name "*.gpg" -mtime +"$RETENTION_DAYS" -delete || true
    
    # S3 cleanup (using lifecycle policy is preferred, but this is a fallback)
    aws s3 ls "s3://$S3_BUCKET/backups/${ENVIRONMENT}/" --recursive | \
        awk -v cutoff="$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d)" '$1 < cutoff {print $4}' | \
        while read -r key; do
            if [[ -n "$key" ]]; then
                aws s3 rm "s3://$S3_BUCKET/$key" || true
                log "INFO" "Deleted old backup: $key"
            fi
        done
}

# Generate backup report
generate_report() {
    local backup_s3_path="$1"
    local backup_size
    backup_size=$(aws s3 ls "$backup_s3_path" | awk '{print $3}')
    
    cat << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "backup_type": "base",
  "s3_path": "$backup_s3_path",
  "size_bytes": $backup_size,
  "retention_days": $RETENTION_DAYS,
  "database": {
    "host": "$DB_HOST",
    "port": $DB_PORT,
    "name": "$DB_NAME"
  },
  "encryption": {
    "enabled": true,
    "key_id": "$BACKUP_ENCRYPTION_KEY_ID"
  },
  "status": "completed"
}
EOF
}

# Main execution
main() {
    log "INFO" "Starting PMS backup process for environment: $ENVIRONMENT"
    
    # Setup
    check_prerequisites
    
    # Create backup
    local backup_path
    backup_path=$(create_base_backup)
    
    # Encrypt backup
    local encrypted_backup
    encrypted_backup=$(encrypt_backup "$backup_path")
    
    # Upload to S3
    local s3_path
    s3_path=$(upload_to_s3 "$encrypted_backup")
    
    # Verify backup
    verify_backup "$s3_path"
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Generate report
    generate_report "$s3_path" > "$BACKUP_DIR/backup_report_$(date +%Y%m%d_%H%M%S).json"
    
    # Cleanup local encrypted backup
    rm -f "$encrypted_backup"
    
    log "INFO" "Backup process completed successfully"
    log "INFO" "Backup location: $s3_path"
}

# Execute main function
main "$@"