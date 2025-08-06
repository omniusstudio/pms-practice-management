#!/bin/bash

# PostgreSQL Backup Monitoring Script for Mental Health PMS
# HIPAA-compliant backup monitoring and alerting
# Usage: ./monitor_backups.sh

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/pms/backup_monitor.log"
S3_BUCKET="${BACKUP_S3_BUCKET:-pms-backups}"
MAX_BACKUP_AGE_HOURS="${MAX_BACKUP_AGE_HOURS:-26}"  # 26 hours for daily backups
MIN_BACKUP_SIZE_MB="${MIN_BACKUP_SIZE_MB:-100}"     # Minimum expected backup size
ALERT_WEBHOOK_URL="${BACKUP_ALERT_WEBHOOK_URL:-}"
SLACK_CHANNEL="${BACKUP_SLACK_CHANNEL:-#alerts}"
PROMETHEUS_PUSHGATEWAY="${PROMETHEUS_PUSHGATEWAY:-}"
ENVIRONMENT="${ENVIRONMENT:-production}"

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

# Send alert function
send_alert() {
    local severity="$1"
    local message="$2"
    local details="${3:-}"

    log "$severity" "ALERT: $message"

    # Prepare alert payload
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    local alert_payload
    alert_payload=$(cat << EOF
{
  "timestamp": "$timestamp",
  "environment": "$ENVIRONMENT",
  "service": "pms-backup-monitor",
  "severity": "$severity",
  "message": "$message",
  "details": "$details",
  "runbook": "https://docs.pms.internal/runbooks/backup-alerts"
}
EOF
    )

    # Send to webhook if configured
    if [[ -n "$ALERT_WEBHOOK_URL" ]]; then
        curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "$alert_payload" \
            "$ALERT_WEBHOOK_URL" || log "WARN" "Failed to send webhook alert"
    fi

    # Send to Slack if configured
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local slack_payload
        slack_payload=$(cat << EOF
{
  "channel": "$SLACK_CHANNEL",
  "username": "PMS Backup Monitor",
  "icon_emoji": ":warning:",
  "attachments": [
    {
      "color": "$([ "$severity" = "CRITICAL" ] && echo "danger" || echo "warning")",
      "title": "Backup Alert - $severity",
      "text": "$message",
      "fields": [
        {
          "title": "Environment",
          "value": "$ENVIRONMENT",
          "short": true
        },
        {
          "title": "Timestamp",
          "value": "$timestamp",
          "short": true
        }
      ],
      "footer": "PMS Backup Monitor"
    }
  ]
}
EOF
        )

        curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "$slack_payload" \
            "$SLACK_WEBHOOK_URL" || log "WARN" "Failed to send Slack alert"
    fi
}

# Send metrics to Prometheus
send_metrics() {
    local metric_name="$1"
    local metric_value="$2"
    local metric_labels="${3:-}"

    if [[ -n "$PROMETHEUS_PUSHGATEWAY" ]]; then
        local labels="environment=\"$ENVIRONMENT\",service=\"pms-backup\""
        if [[ -n "$metric_labels" ]]; then
            labels="$labels,$metric_labels"
        fi

        local metric_data="$metric_name{$labels} $metric_value"

        echo "$metric_data" | curl -s --data-binary @- \
            "$PROMETHEUS_PUSHGATEWAY/metrics/job/pms-backup-monitor" || \
            log "WARN" "Failed to send metrics to Prometheus"
    fi
}

# Check backup freshness
check_backup_freshness() {
    log "INFO" "Checking backup freshness"

    # Get latest backup
    local latest_backup
    latest_backup=$(aws s3 ls "s3://$S3_BUCKET/backups/" --recursive | \
        grep '\.gpg$' | \
        sort -k1,2 | \
        tail -1)

    if [[ -z "$latest_backup" ]]; then
        send_alert "CRITICAL" "No backups found in S3 bucket" "Bucket: s3://$S3_BUCKET/backups/"
        send_metrics "pms_backup_exists" "0"
        return 1
    fi

    # Parse backup timestamp
    local backup_date
    local backup_time
    backup_date=$(echo "$latest_backup" | awk '{print $1}')
    backup_time=$(echo "$latest_backup" | awk '{print $2}')
    local backup_file
    backup_file=$(echo "$latest_backup" | awk '{print $4}')

    # Convert to epoch time
    local backup_timestamp
    backup_timestamp=$(date -d "$backup_date $backup_time" +%s 2>/dev/null || \
                      date -j -f "%Y-%m-%d %H:%M:%S" "$backup_date $backup_time" +%s 2>/dev/null)

    local current_timestamp
    current_timestamp=$(date +%s)

    local age_hours
    age_hours=$(( (current_timestamp - backup_timestamp) / 3600 ))

    log "INFO" "Latest backup: $backup_file (age: ${age_hours}h)"

    # Check if backup is too old
    if [[ $age_hours -gt $MAX_BACKUP_AGE_HOURS ]]; then
        send_alert "CRITICAL" "Backup is too old" "Latest backup: $backup_file, Age: ${age_hours}h, Max allowed: ${MAX_BACKUP_AGE_HOURS}h"
        send_metrics "pms_backup_age_hours" "$age_hours" "status=\"stale\""
        return 1
    fi

    send_metrics "pms_backup_exists" "1"
    send_metrics "pms_backup_age_hours" "$age_hours" "status=\"fresh\""
    log "INFO" "Backup freshness check passed"
    return 0
}

# Check backup size
check_backup_size() {
    log "INFO" "Checking backup size"

    # Get latest backup info
    local latest_backup
    latest_backup=$(aws s3 ls "s3://$S3_BUCKET/backups/" --recursive | \
        grep '\.gpg$' | \
        sort -k1,2 | \
        tail -1)

    if [[ -z "$latest_backup" ]]; then
        log "ERROR" "No backup found for size check"
        return 1
    fi

    local backup_size_bytes
    backup_size_bytes=$(echo "$latest_backup" | awk '{print $3}')
    local backup_file
    backup_file=$(echo "$latest_backup" | awk '{print $4}')

    local backup_size_mb
    backup_size_mb=$((backup_size_bytes / 1024 / 1024))

    log "INFO" "Latest backup size: ${backup_size_mb}MB"

    # Check if backup is too small
    if [[ $backup_size_mb -lt $MIN_BACKUP_SIZE_MB ]]; then
        send_alert "WARNING" "Backup size is suspiciously small" "Backup: $backup_file, Size: ${backup_size_mb}MB, Min expected: ${MIN_BACKUP_SIZE_MB}MB"
        send_metrics "pms_backup_size_mb" "$backup_size_mb" "status=\"small\""
        return 1
    fi

    send_metrics "pms_backup_size_mb" "$backup_size_mb" "status=\"normal\""
    log "INFO" "Backup size check passed"
    return 0
}

# Check backup count and retention
check_backup_retention() {
    log "INFO" "Checking backup retention"

    # Count backups
    local backup_count
    backup_count=$(aws s3 ls "s3://$S3_BUCKET/backups/" --recursive | \
        grep '\.gpg$' | \
        wc -l | \
        tr -d ' ')

    log "INFO" "Total backups in S3: $backup_count"

    # Check minimum backup count (should have at least 7 daily backups)
    local min_backup_count=7
    if [[ $backup_count -lt $min_backup_count ]]; then
        send_alert "WARNING" "Low backup count" "Current: $backup_count, Expected minimum: $min_backup_count"
        send_metrics "pms_backup_count" "$backup_count" "status=\"low\""
    else
        send_metrics "pms_backup_count" "$backup_count" "status=\"normal\""
    fi

    # Check for backups older than retention period (30 days)
    local retention_days=30
    local cutoff_timestamp
    cutoff_timestamp=$(date -d "$retention_days days ago" +%s 2>/dev/null || \
                      date -j -v-${retention_days}d +%s 2>/dev/null)

    local old_backups
    old_backups=$(aws s3 ls "s3://$S3_BUCKET/backups/" --recursive | \
        grep '\.gpg$' | \
        while read -r line; do
            local backup_date backup_time
            backup_date=$(echo "$line" | awk '{print $1}')
            backup_time=$(echo "$line" | awk '{print $2}')
            local backup_timestamp
            backup_timestamp=$(date -d "$backup_date $backup_time" +%s 2>/dev/null || \
                              date -j -f "%Y-%m-%d %H:%M:%S" "$backup_date $backup_time" +%s 2>/dev/null)

            if [[ $backup_timestamp -lt $cutoff_timestamp ]]; then
                echo "$line"
            fi
        done)

    local old_backup_count
    old_backup_count=$(echo "$old_backups" | grep -c '.' || echo "0")

    if [[ $old_backup_count -gt 0 ]]; then
        send_alert "INFO" "Old backups found" "$old_backup_count backups older than $retention_days days found. Consider cleanup."
        send_metrics "pms_backup_old_count" "$old_backup_count"
    else
        send_metrics "pms_backup_old_count" "0"
    fi

    log "INFO" "Backup retention check completed"
    return 0
}

# Check S3 bucket accessibility
check_s3_accessibility() {
    log "INFO" "Checking S3 bucket accessibility"

    # Test S3 access
    if ! aws s3 ls "s3://$S3_BUCKET/" >/dev/null 2>&1; then
        send_alert "CRITICAL" "S3 bucket not accessible" "Bucket: s3://$S3_BUCKET/"
        send_metrics "pms_backup_s3_accessible" "0"
        return 1
    fi

    send_metrics "pms_backup_s3_accessible" "1"
    log "INFO" "S3 bucket accessibility check passed"
    return 0
}

# Check backup process health
check_backup_process() {
    log "INFO" "Checking backup process health"

    # Check if backup process is running
    local backup_processes
    backup_processes=$(pgrep -f "pg_backup.sh" | wc -l | tr -d ' ')

    # Check backup log for recent activity
    local backup_log="/var/log/pms/backup.log"
    local recent_backup_activity=0

    if [[ -f "$backup_log" ]]; then
        # Check for backup activity in the last 2 hours
        local two_hours_ago
        two_hours_ago=$(date -d "2 hours ago" "+%Y-%m-%d %H:%M" 2>/dev/null || \
                       date -j -v-2H "+%Y-%m-%d %H:%M" 2>/dev/null)

        if grep -q "$two_hours_ago" "$backup_log" 2>/dev/null; then
            recent_backup_activity=1
        fi
    fi

    send_metrics "pms_backup_process_running" "$backup_processes"
    send_metrics "pms_backup_recent_activity" "$recent_backup_activity"

    log "INFO" "Backup processes running: $backup_processes"
    log "INFO" "Recent backup activity: $recent_backup_activity"

    return 0
}

# Check encryption key availability
check_encryption_key() {
    log "INFO" "Checking backup encryption key"

    local key_id="${BACKUP_ENCRYPTION_KEY_ID:-}"
    if [[ -z "$key_id" ]]; then
        send_alert "CRITICAL" "Backup encryption key ID not configured" "BACKUP_ENCRYPTION_KEY_ID environment variable not set"
        send_metrics "pms_backup_encryption_key_available" "0"
        return 1
    fi

    # Test GPG key availability
    if ! gpg --list-secret-keys "$key_id" >/dev/null 2>&1; then
        send_alert "CRITICAL" "Backup encryption key not available" "Key ID: $key_id"
        send_metrics "pms_backup_encryption_key_available" "0"
        return 1
    fi

    send_metrics "pms_backup_encryption_key_available" "1"
    log "INFO" "Encryption key check passed"
    return 0
}

# Generate monitoring report
generate_monitoring_report() {
    local overall_status="$1"
    local checks_passed="$2"
    local total_checks="$3"

    local report_file="/var/log/pms/backup_monitoring_$(date +%Y%m%d_%H%M%S).json"

    cat << EOF > "$report_file"
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "overall_status": "$overall_status",
  "checks": {
    "passed": $checks_passed,
    "total": $total_checks,
    "success_rate": $(echo "scale=2; $checks_passed * 100 / $total_checks" | bc -l 2>/dev/null || echo "0")
  },
  "s3_bucket": "$S3_BUCKET",
  "max_backup_age_hours": $MAX_BACKUP_AGE_HOURS,
  "min_backup_size_mb": $MIN_BACKUP_SIZE_MB,
  "next_check": "$(date -d "+1 hour" -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -j -v+1H -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)"
}
EOF

    log "INFO" "Monitoring report generated: $report_file"
    echo "$report_file"
}

# Main monitoring function
main() {
    log "INFO" "Starting backup monitoring"

    local checks_passed=0
    local total_checks=6
    local overall_status="healthy"

    # Run all checks
    if check_s3_accessibility; then
        ((checks_passed++))
    else
        overall_status="unhealthy"
    fi

    if check_encryption_key; then
        ((checks_passed++))
    else
        overall_status="unhealthy"
    fi

    if check_backup_freshness; then
        ((checks_passed++))
    else
        overall_status="unhealthy"
    fi

    if check_backup_size; then
        ((checks_passed++))
    else
        overall_status="degraded"
    fi

    if check_backup_retention; then
        ((checks_passed++))
    else
        overall_status="degraded"
    fi

    if check_backup_process; then
        ((checks_passed++))
    fi

    # Send overall health metric
    local health_score
    health_score=$(echo "scale=2; $checks_passed * 100 / $total_checks" | bc -l 2>/dev/null || echo "0")
    send_metrics "pms_backup_health_score" "$health_score"

    # Generate report
    local report_file
    report_file=$(generate_monitoring_report "$overall_status" "$checks_passed" "$total_checks")

    # Send summary alert if unhealthy
    if [[ "$overall_status" == "unhealthy" ]]; then
        send_alert "CRITICAL" "Backup system is unhealthy" "Checks passed: $checks_passed/$total_checks. See report: $report_file"
    elif [[ "$overall_status" == "degraded" ]]; then
        send_alert "WARNING" "Backup system is degraded" "Checks passed: $checks_passed/$total_checks. See report: $report_file"
    fi

    log "INFO" "Backup monitoring completed"
    log "INFO" "Overall status: $overall_status ($checks_passed/$total_checks checks passed)"

    # Exit with appropriate code
    if [[ "$overall_status" == "unhealthy" ]]; then
        exit 1
    elif [[ "$overall_status" == "degraded" ]]; then
        exit 2
    else
        exit 0
    fi
}

# Execute main function
main "$@"
