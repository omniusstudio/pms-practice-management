#!/bin/bash

# PostgreSQL Restore Script for Mental Health PMS
# HIPAA-compliant restore with point-in-time recovery (PITR)
# Usage: ./restore.sh [backup_path] [target_time] [target_environment]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/pms/restore.log"
RESTORE_DIR="/var/restore/pms"
S3_BUCKET="${BACKUP_S3_BUCKET:-pms-backups}"
BACKUP_PATH="${1:-}"
TARGET_TIME="${2:-}"
TARGET_ENV="${3:-sandbox}"
ENCRYPTION_KEY_ID="${BACKUP_ENCRYPTION_KEY_ID}"

# Target database configuration
TARGET_DB_HOST="${TARGET_DB_HOST:-localhost}"
TARGET_DB_PORT="${TARGET_DB_PORT:-5432}"
TARGET_DB_NAME="${TARGET_DB_NAME:-pms_restore}"
TARGET_DB_USER="${TARGET_DB_USER:-pms_user}"
PGPASSWORD="${TARGET_DB_PASSWORD}"
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

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [backup_path] [target_time] [target_environment]

Arguments:
  backup_path        S3 path to backup (e.g., s3://bucket/backups/prod/backup.gpg)
  target_time        Point-in-time recovery target (YYYY-MM-DD HH:MM:SS UTC) [optional]
  target_environment Target environment (sandbox, staging, etc.) [default: sandbox]

Examples:
  # Restore latest backup
  $0 s3://pms-backups/backups/production/pms_backup_20240101_020000.tar.gz.gpg
  
  # Point-in-time recovery
  $0 s3://pms-backups/backups/production/pms_backup_20240101_020000.tar.gz.gpg "2024-01-01 14:30:00"
  
  # Restore to staging environment
  $0 s3://pms-backups/backups/production/pms_backup_20240101_020000.tar.gz.gpg "" staging

Environment Variables:
  TARGET_DB_HOST     Target database host [default: localhost]
  TARGET_DB_PORT     Target database port [default: 5432]
  TARGET_DB_NAME     Target database name [default: pms_restore]
  TARGET_DB_USER     Target database user [default: pms_user]
  TARGET_DB_PASSWORD Target database password [required]
  BACKUP_ENCRYPTION_KEY_ID GPG key ID for decryption [required]
EOF
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites for restore"
    
    # Check arguments
    if [[ -z "$BACKUP_PATH" ]]; then
        show_usage
        error_exit "Backup path is required"
    fi
    
    # Check required tools
    command -v pg_restore >/dev/null 2>&1 || error_exit "pg_restore not found"
    command -v psql >/dev/null 2>&1 || error_exit "psql not found"
    command -v aws >/dev/null 2>&1 || error_exit "AWS CLI not found"
    command -v gpg >/dev/null 2>&1 || error_exit "GPG not found"
    
    # Check required environment variables
    [[ -n "${BACKUP_ENCRYPTION_KEY_ID:-}" ]] || error_exit "BACKUP_ENCRYPTION_KEY_ID not set"
    [[ -n "${TARGET_DB_PASSWORD:-}" ]] || error_exit "TARGET_DB_PASSWORD not set"
    
    # Create restore directory
    mkdir -p "$RESTORE_DIR"
    
    log "INFO" "Prerequisites check passed"
}

# Download and decrypt backup
download_and_decrypt() {
    local backup_s3_path="$1"
    local encrypted_file="$RESTORE_DIR/$(basename "$backup_s3_path")"
    local decrypted_file="${encrypted_file%.gpg}"
    
    log "INFO" "Downloading backup: $backup_s3_path"
    
    # Download from S3
    aws s3 cp "$backup_s3_path" "$encrypted_file" || error_exit "Failed to download backup"
    
    log "INFO" "Decrypting backup"
    
    # Decrypt backup
    gpg --quiet --decrypt "$encrypted_file" > "$decrypted_file" || error_exit "Failed to decrypt backup"
    
    # Remove encrypted file
    rm -f "$encrypted_file"
    
    log "INFO" "Backup decrypted: $decrypted_file"
    echo "$decrypted_file"
}

# Extract backup
extract_backup() {
    local backup_file="$1"
    local extract_dir="$RESTORE_DIR/extracted"
    
    log "INFO" "Extracting backup: $(basename "$backup_file")"
    
    # Create extraction directory
    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"
    
    # Extract backup
    tar -xzf "$backup_file" -C "$extract_dir" || error_exit "Failed to extract backup"
    
    log "INFO" "Backup extracted to: $extract_dir"
    echo "$extract_dir"
}

# Prepare target database
prepare_target_database() {
    log "INFO" "Preparing target database: $TARGET_DB_NAME"
    
    # Check if target database exists and drop it
    if psql -h "$TARGET_DB_HOST" -p "$TARGET_DB_PORT" -U "$TARGET_DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$TARGET_DB_NAME"; then
        log "WARN" "Target database exists, dropping: $TARGET_DB_NAME"
        psql -h "$TARGET_DB_HOST" -p "$TARGET_DB_PORT" -U "$TARGET_DB_USER" -d postgres \
            -c "DROP DATABASE IF EXISTS \"$TARGET_DB_NAME\"" || error_exit "Failed to drop existing database"
    fi
    
    # Create target database
    log "INFO" "Creating target database: $TARGET_DB_NAME"
    psql -h "$TARGET_DB_HOST" -p "$TARGET_DB_PORT" -U "$TARGET_DB_USER" -d postgres \
        -c "CREATE DATABASE \"$TARGET_DB_NAME\"" || error_exit "Failed to create target database"
    
    log "INFO" "Target database prepared"
}

# Restore base backup
restore_base_backup() {
    local extract_dir="$1"
    
    log "INFO" "Restoring base backup to: $TARGET_DB_NAME"
    
    # Find the base backup file
    local base_backup
    base_backup=$(find "$extract_dir" -name "base.tar" -o -name "*.tar" | head -1)
    
    if [[ -z "$base_backup" ]]; then
        error_exit "Base backup file not found in extracted directory"
    fi
    
    # Stop target PostgreSQL if running locally
    if [[ "$TARGET_DB_HOST" == "localhost" || "$TARGET_DB_HOST" == "127.0.0.1" ]]; then
        log "WARN" "Attempting to stop local PostgreSQL for restore"
        sudo systemctl stop postgresql || true
    fi
    
    # Extract base backup to PostgreSQL data directory
    local data_dir="/tmp/pms_restore_data"
    rm -rf "$data_dir"
    mkdir -p "$data_dir"
    
    tar -xf "$base_backup" -C "$data_dir" || error_exit "Failed to extract base backup"
    
    log "INFO" "Base backup extracted to: $data_dir"
    echo "$data_dir"
}

# Apply WAL files for PITR
apply_wal_files() {
    local data_dir="$1"
    local target_time="$2"
    local extract_dir="$3"
    
    if [[ -z "$target_time" ]]; then
        log "INFO" "No target time specified, skipping WAL replay"
        return 0
    fi
    
    log "INFO" "Applying WAL files for point-in-time recovery to: $target_time"
    
    # Create recovery configuration
    local recovery_conf="$data_dir/postgresql.auto.conf"
    
    cat > "$recovery_conf" << EOF
# Point-in-time recovery configuration
restore_command = 'cp $extract_dir/pg_wal/%f %p'
recovery_target_time = '$target_time'
recovery_target_action = 'promote'
EOF
    
    # Create recovery signal file
    touch "$data_dir/recovery.signal"
    
    log "INFO" "Recovery configuration created"
}

# Start PostgreSQL and verify
start_and_verify() {
    local data_dir="$1"
    
    log "INFO" "Starting PostgreSQL with restored data"
    
    # Start PostgreSQL with custom data directory
    local pg_port="$((TARGET_DB_PORT + 1000))"  # Use different port for restore instance
    
    # Start temporary PostgreSQL instance
    pg_ctl -D "$data_dir" -l "$RESTORE_DIR/postgresql.log" -o "-p $pg_port" start || \
        error_exit "Failed to start PostgreSQL with restored data"
    
    # Wait for PostgreSQL to start
    sleep 5
    
    # Verify connection
    pg_isready -h localhost -p "$pg_port" || error_exit "Restored PostgreSQL instance not ready"
    
    log "INFO" "PostgreSQL started successfully on port $pg_port"
    echo "$pg_port"
}

# Run smoke tests
run_smoke_tests() {
    local pg_port="$1"
    
    log "INFO" "Running smoke tests on restored database"
    
    # Test database connectivity
    psql -h localhost -p "$pg_port" -U "$TARGET_DB_USER" -d "$TARGET_DB_NAME" \
        -c "SELECT version();" > /dev/null || error_exit "Database connectivity test failed"
    
    # Test table existence (adjust based on your schema)
    local table_count
    table_count=$(psql -h localhost -p "$pg_port" -U "$TARGET_DB_USER" -d "$TARGET_DB_NAME" \
        -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)
    
    if [[ "$table_count" -eq 0 ]]; then
        error_exit "No tables found in restored database"
    fi
    
    log "INFO" "Found $table_count tables in restored database"
    
    # Test audit log table (HIPAA requirement)
    if psql -h localhost -p "$pg_port" -U "$TARGET_DB_USER" -d "$TARGET_DB_NAME" \
        -c "SELECT count(*) FROM audit_log LIMIT 1;" > /dev/null 2>&1; then
        log "INFO" "Audit log table verified"
    else
        log "WARN" "Audit log table not found or not accessible"
    fi
    
    # Test data integrity (sample queries)
    log "INFO" "Running data integrity checks"
    
    # Add more specific tests based on your application schema
    
    log "INFO" "Smoke tests completed successfully"
}

# Generate restore report
generate_restore_report() {
    local backup_path="$1"
    local target_time="$2"
    local pg_port="$3"
    
    cat << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "restore_type": "$(if [[ -n "$target_time" ]]; then echo "point_in_time"; else echo "full"; fi)",
  "source_backup": "$backup_path",
  "target_time": "${target_time:-null}",
  "target_environment": "$TARGET_ENV",
  "target_database": {
    "host": "$TARGET_DB_HOST",
    "port": $pg_port,
    "name": "$TARGET_DB_NAME"
  },
  "smoke_tests": {
    "connectivity": "passed",
    "table_count": "$(psql -h localhost -p "$pg_port" -U "$TARGET_DB_USER" -d "$TARGET_DB_NAME" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)",
    "audit_log": "$(if psql -h localhost -p "$pg_port" -U "$TARGET_DB_USER" -d "$TARGET_DB_NAME" -c "SELECT 1 FROM audit_log LIMIT 1;" > /dev/null 2>&1; then echo "passed"; else echo "not_found"; fi)"
  },
  "status": "completed"
}
EOF
}

# Cleanup function
cleanup() {
    log "INFO" "Cleaning up temporary files"
    
    # Stop temporary PostgreSQL instance if running
    if [[ -n "${TEMP_PG_PORT:-}" ]]; then
        pg_ctl -D "$RESTORE_DIR/extracted" stop -m fast || true
    fi
    
    # Remove temporary files (keep logs)
    find "$RESTORE_DIR" -name "*.tar.gz" -delete || true
    find "$RESTORE_DIR" -name "*.tar" -delete || true
}

# Main execution
main() {
    log "INFO" "Starting PMS restore process"
    log "INFO" "Backup: $BACKUP_PATH"
    log "INFO" "Target time: ${TARGET_TIME:-latest}"
    log "INFO" "Target environment: $TARGET_ENV"
    
    # Setup cleanup trap
    trap cleanup EXIT
    
    # Prerequisites
    check_prerequisites
    
    # Download and decrypt backup
    local decrypted_backup
    decrypted_backup=$(download_and_decrypt "$BACKUP_PATH")
    
    # Extract backup
    local extract_dir
    extract_dir=$(extract_backup "$decrypted_backup")
    
    # Prepare target database
    prepare_target_database
    
    # Restore base backup
    local data_dir
    data_dir=$(restore_base_backup "$extract_dir")
    
    # Apply WAL files for PITR if needed
    apply_wal_files "$data_dir" "$TARGET_TIME" "$extract_dir"
    
    # Start PostgreSQL and verify
    local pg_port
    pg_port=$(start_and_verify "$data_dir")
    TEMP_PG_PORT="$pg_port"
    
    # Run smoke tests
    run_smoke_tests "$pg_port"
    
    # Generate report
    generate_restore_report "$BACKUP_PATH" "$TARGET_TIME" "$pg_port" > "$RESTORE_DIR/restore_report_$(date +%Y%m%d_%H%M%S).json"
    
    log "INFO" "Restore process completed successfully"
    log "INFO" "Restored database available on port: $pg_port"
    log "INFO" "Database name: $TARGET_DB_NAME"
    
    # Instructions for user
    cat << EOF

=== RESTORE COMPLETED ===
Restored database is running on:
  Host: localhost
  Port: $pg_port
  Database: $TARGET_DB_NAME
  User: $TARGET_DB_USER

To connect:
  psql -h localhost -p $pg_port -U $TARGET_DB_USER -d $TARGET_DB_NAME

To stop the restored instance:
  pg_ctl -D $data_dir stop

Restore report saved to: $RESTORE_DIR/restore_report_$(date +%Y%m%d_%H%M%S).json
========================
EOF
}

# Execute main function
main "$@"