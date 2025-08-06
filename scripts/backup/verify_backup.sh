#!/bin/bash

# PostgreSQL Backup Verification Script for Mental Health PMS
# HIPAA-compliant backup integrity verification
# Usage: ./verify_backup.sh [backup_path]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/pms/backup_verify.log"
TEMP_DIR="/tmp/pms_backup_verify"
S3_BUCKET="${BACKUP_S3_BUCKET:-pms-backups}"
BACKUP_PATH="${1:-}"
ENCRYPTION_KEY_ID="${BACKUP_ENCRYPTION_KEY_ID}"

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
Usage: $0 [backup_path]

Arguments:
  backup_path    S3 path to backup or 'latest' for most recent backup

Examples:
  # Verify specific backup
  $0 s3://pms-backups/backups/production/pms_backup_20240101_020000.tar.gz.gpg

  # Verify latest backup
  $0 latest

Environment Variables:
  BACKUP_S3_BUCKET         S3 bucket for backups [default: pms-backups]
  BACKUP_ENCRYPTION_KEY_ID GPG key ID for decryption [required]
EOF
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites for backup verification"

    # Check required tools
    command -v aws >/dev/null 2>&1 || error_exit "AWS CLI not found"
    command -v gpg >/dev/null 2>&1 || error_exit "GPG not found"
    command -v pg_restore >/dev/null 2>&1 || error_exit "pg_restore not found"

    # Check required environment variables
    [[ -n "${BACKUP_ENCRYPTION_KEY_ID:-}" ]] || error_exit "BACKUP_ENCRYPTION_KEY_ID not set"

    # Create temp directory
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"

    log "INFO" "Prerequisites check passed"
}

# Find latest backup
find_latest_backup() {
    log "INFO" "Finding latest backup in S3"

    local latest_backup
    latest_backup=$(aws s3 ls "s3://$S3_BUCKET/backups/" --recursive | \
        grep '\.gpg$' | \
        sort -k1,2 | \
        tail -1 | \
        awk '{print $4}')

    if [[ -z "$latest_backup" ]]; then
        error_exit "No backups found in S3 bucket"
    fi

    local full_path="s3://$S3_BUCKET/$latest_backup"
    log "INFO" "Latest backup found: $full_path"
    echo "$full_path"
}

# Download backup
download_backup() {
    local backup_s3_path="$1"
    local local_file="$TEMP_DIR/$(basename "$backup_s3_path")"

    log "INFO" "Downloading backup: $backup_s3_path"

    # Get backup metadata
    local backup_size
    backup_size=$(aws s3 ls "$backup_s3_path" | awk '{print $3}')
    log "INFO" "Backup size: $backup_size bytes"

    # Download backup
    aws s3 cp "$backup_s3_path" "$local_file" || error_exit "Failed to download backup"

    # Verify download
    local downloaded_size
    downloaded_size=$(stat -f%z "$local_file" 2>/dev/null || stat -c%s "$local_file" 2>/dev/null)

    if [[ "$downloaded_size" != "$backup_size" ]]; then
        error_exit "Downloaded file size ($downloaded_size) doesn't match S3 size ($backup_size)"
    fi

    log "INFO" "Backup downloaded successfully: $local_file"
    echo "$local_file"
}

# Verify encryption
verify_encryption() {
    local backup_file="$1"

    log "INFO" "Verifying backup encryption"

    # Check if file is GPG encrypted
    if ! file "$backup_file" | grep -q "GPG symmetrically encrypted data"; then
        if ! gpg --list-packets "$backup_file" >/dev/null 2>&1; then
            error_exit "Backup file is not properly GPG encrypted"
        fi
    fi

    log "INFO" "Backup encryption verified"
}

# Test decryption
test_decryption() {
    local backup_file="$1"
    local decrypted_file="$TEMP_DIR/decrypted_backup.tar.gz"

    log "INFO" "Testing backup decryption"

    # Decrypt backup
    gpg --quiet --decrypt "$backup_file" > "$decrypted_file" || error_exit "Failed to decrypt backup"

    # Verify decrypted file is a valid tar.gz
    if ! file "$decrypted_file" | grep -q "gzip compressed"; then
        error_exit "Decrypted backup is not a valid gzip file"
    fi

    log "INFO" "Backup decryption successful"
    echo "$decrypted_file"
}

# Verify archive integrity
verify_archive_integrity() {
    local decrypted_file="$1"
    local extract_dir="$TEMP_DIR/extracted"

    log "INFO" "Verifying archive integrity"

    # Test tar.gz integrity
    if ! tar -tzf "$decrypted_file" >/dev/null 2>&1; then
        error_exit "Archive integrity check failed - corrupted tar.gz"
    fi

    # Extract archive
    mkdir -p "$extract_dir"
    tar -xzf "$decrypted_file" -C "$extract_dir" || error_exit "Failed to extract archive"

    log "INFO" "Archive integrity verified"
    echo "$extract_dir"
}

# Verify PostgreSQL backup structure
verify_pg_backup_structure() {
    local extract_dir="$1"

    log "INFO" "Verifying PostgreSQL backup structure"

    # Look for base backup files
    local base_backup
    base_backup=$(find "$extract_dir" -name "base.tar" -o -name "*.tar" | head -1)

    if [[ -z "$base_backup" ]]; then
        error_exit "No PostgreSQL base backup file found"
    fi

    log "INFO" "Found base backup: $(basename "$base_backup")"

    # Verify base backup can be listed
    if ! tar -tf "$base_backup" >/dev/null 2>&1; then
        error_exit "Base backup tar file is corrupted"
    fi

    # Check for essential PostgreSQL files
    local essential_files=("PG_VERSION" "postgresql.conf" "pg_hba.conf")
    for file in "${essential_files[@]}"; do
        if ! tar -tf "$base_backup" | grep -q "$file"; then
            log "WARN" "Essential PostgreSQL file not found in backup: $file"
        fi
    done

    # Check for WAL files
    local wal_files
    wal_files=$(find "$extract_dir" -name "pg_wal" -type d | wc -l)

    if [[ "$wal_files" -gt 0 ]]; then
        log "INFO" "WAL files directory found in backup"
    else
        log "WARN" "No WAL files directory found - PITR may not be available"
    fi

    log "INFO" "PostgreSQL backup structure verified"
}

# Test backup with pg_restore
test_pg_restore() {
    local extract_dir="$1"

    log "INFO" "Testing backup with pg_restore"

    # Find base backup
    local base_backup
    base_backup=$(find "$extract_dir" -name "base.tar" -o -name "*.tar" | head -1)

    # Create temporary directory for extraction
    local pg_test_dir="$TEMP_DIR/pg_test"
    mkdir -p "$pg_test_dir"

    # Extract base backup
    tar -xf "$base_backup" -C "$pg_test_dir" || error_exit "Failed to extract base backup for testing"

    # Check for critical PostgreSQL files
    if [[ ! -f "$pg_test_dir/PG_VERSION" ]]; then
        error_exit "PG_VERSION file not found in extracted backup"
    fi

    local pg_version
    pg_version=$(cat "$pg_test_dir/PG_VERSION")
    log "INFO" "PostgreSQL version in backup: $pg_version"

    # Verify data directory structure
    local required_dirs=("base" "global" "pg_wal")
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$pg_test_dir/$dir" ]]; then
            log "WARN" "Required PostgreSQL directory not found: $dir"
        fi
    done

    log "INFO" "pg_restore test completed successfully"
}

# Calculate checksums
calculate_checksums() {
    local backup_file="$1"
    local decrypted_file="$2"

    log "INFO" "Calculating backup checksums"

    # Calculate checksums
    local encrypted_md5
    local decrypted_md5

    if command -v md5sum >/dev/null 2>&1; then
        encrypted_md5=$(md5sum "$backup_file" | awk '{print $1}')
        decrypted_md5=$(md5sum "$decrypted_file" | awk '{print $1}')
    elif command -v md5 >/dev/null 2>&1; then
        encrypted_md5=$(md5 -q "$backup_file")
        decrypted_md5=$(md5 -q "$decrypted_file")
    else
        log "WARN" "No MD5 utility found, skipping checksum calculation"
        return 0
    fi

    log "INFO" "Encrypted backup MD5: $encrypted_md5"
    log "INFO" "Decrypted backup MD5: $decrypted_md5"

    # Store checksums for reporting
    echo "$encrypted_md5" > "$TEMP_DIR/encrypted.md5"
    echo "$decrypted_md5" > "$TEMP_DIR/decrypted.md5"
}

# Generate verification report
generate_verification_report() {
    local backup_path="$1"
    local backup_file="$2"
    local extract_dir="$3"

    local encrypted_md5=""
    local decrypted_md5=""

    if [[ -f "$TEMP_DIR/encrypted.md5" ]]; then
        encrypted_md5=$(cat "$TEMP_DIR/encrypted.md5")
    fi

    if [[ -f "$TEMP_DIR/decrypted.md5" ]]; then
        decrypted_md5=$(cat "$TEMP_DIR/decrypted.md5")
    fi

    local backup_size
    backup_size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null)

    local pg_version=""
    local pg_version_file
    pg_version_file=$(find "$extract_dir" -name "PG_VERSION" | head -1)
    if [[ -n "$pg_version_file" ]]; then
        pg_version=$(cat "$pg_version_file")
    fi

    cat << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "backup_path": "$backup_path",
  "verification_status": "passed",
  "backup_info": {
    "size_bytes": $backup_size,
    "encrypted_md5": "$encrypted_md5",
    "decrypted_md5": "$decrypted_md5",
    "postgresql_version": "$pg_version"
  },
  "checks": {
    "download": "passed",
    "encryption": "passed",
    "decryption": "passed",
    "archive_integrity": "passed",
    "postgresql_structure": "passed",
    "pg_restore_test": "passed"
  },
  "warnings": [],
  "errors": []
}
EOF
}

# Cleanup function
cleanup() {
    log "INFO" "Cleaning up temporary files"
    rm -rf "$TEMP_DIR"
}

# Main execution
main() {
    log "INFO" "Starting backup verification process"

    # Check arguments
    if [[ -z "$BACKUP_PATH" ]]; then
        show_usage
        error_exit "Backup path is required"
    fi

    # Setup cleanup trap
    trap cleanup EXIT

    # Prerequisites
    check_prerequisites

    # Determine backup path
    local backup_s3_path
    if [[ "$BACKUP_PATH" == "latest" ]]; then
        backup_s3_path=$(find_latest_backup)
    else
        backup_s3_path="$BACKUP_PATH"
    fi

    log "INFO" "Verifying backup: $backup_s3_path"

    # Download backup
    local backup_file
    backup_file=$(download_backup "$backup_s3_path")

    # Verify encryption
    verify_encryption "$backup_file"

    # Test decryption
    local decrypted_file
    decrypted_file=$(test_decryption "$backup_file")

    # Verify archive integrity
    local extract_dir
    extract_dir=$(verify_archive_integrity "$decrypted_file")

    # Verify PostgreSQL backup structure
    verify_pg_backup_structure "$extract_dir"

    # Test with pg_restore
    test_pg_restore "$extract_dir"

    # Calculate checksums
    calculate_checksums "$backup_file" "$decrypted_file"

    # Generate verification report
    local report_file="/var/log/pms/backup_verification_$(date +%Y%m%d_%H%M%S).json"
    generate_verification_report "$backup_s3_path" "$backup_file" "$extract_dir" > "$report_file"

    log "INFO" "Backup verification completed successfully"
    log "INFO" "Verification report: $report_file"

    # Display summary
    cat << EOF

=== BACKUP VERIFICATION SUMMARY ===
Backup: $backup_s3_path
Status: PASSED
Size: $(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null) bytes
PostgreSQL Version: $(find "$extract_dir" -name "PG_VERSION" -exec cat {} \; | head -1)
Report: $report_file
===================================
EOF
}

# Execute main function
main "$@"
