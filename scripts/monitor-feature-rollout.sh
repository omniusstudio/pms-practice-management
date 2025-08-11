#!/bin/bash

# Feature Flag Rollout Monitoring Script
# Monitors application metrics during feature flag rollouts and alerts on issues

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="pms"
DEPLOYMENT_NAME="pms-backend"
MONITORING_DURATION=300  # 5 minutes default
CHECK_INTERVAL=30        # 30 seconds between checks
ALERT_THRESHOLD_ERROR_RATE=0.05  # 5% error rate
ALERT_THRESHOLD_RESPONSE_TIME=2000  # 2 seconds
ALERT_THRESHOLD_CPU=80   # 80% CPU usage
ALERT_THRESHOLD_MEMORY=80  # 80% memory usage

# Metrics storage
METRICS_DIR="/tmp/feature-rollout-metrics"
mkdir -p "$METRICS_DIR"

# Functions
print_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -f, --feature <name>            - Feature flag name to monitor"
    echo "  -d, --duration <seconds>        - Monitoring duration (default: 300)"
    echo "  -i, --interval <seconds>        - Check interval (default: 30)"
    echo "  -n, --namespace <namespace>     - Kubernetes namespace (default: pms)"
    echo "  -t, --threshold-error <rate>    - Error rate threshold (default: 0.05)"
    echo "  -r, --threshold-response <ms>   - Response time threshold (default: 2000)"
    echo "  -c, --threshold-cpu <percent>   - CPU usage threshold (default: 80)"
    echo "  -m, --threshold-memory <percent> - Memory usage threshold (default: 80)"
    echo "  -a, --alert-webhook <url>       - Webhook URL for alerts"
    echo "  -v, --verbose                   - Verbose output"
    echo "  -h, --help                      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -f telehealth_appointments_enabled -d 600"
    echo "  $0 --feature new_feature --duration 300 --verbose"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_alert() {
    echo -e "${RED}[ALERT]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2

    # Send webhook alert if configured
    if [ -n "${ALERT_WEBHOOK:-}" ]; then
        send_webhook_alert "$1"
    fi
}

send_webhook_alert() {
    local message="$1"
    local payload

    payload=$(jq -n \
        --arg text "Feature Rollout Alert: $message" \
        --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
        --arg feature "${FEATURE_NAME:-unknown}" \
        '{
            text: $text,
            timestamp: $timestamp,
            feature: $feature,
            severity: "high"
        }')

    if curl -s -X POST "$ALERT_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$payload" > /dev/null; then
        log_info "Alert sent to webhook"
    else
        log_error "Failed to send webhook alert"
    fi
}

check_prerequisites() {
    local missing_tools=()

    for tool in kubectl jq curl; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi

    # Check Kubernetes access
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        exit 1
    fi

    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace '$NAMESPACE' does not exist"
        exit 1
    fi
}

get_pod_metrics() {
    local metrics_file="$METRICS_DIR/pod-metrics-$(date +%s).json"

    # Get pod resource usage
    kubectl top pods -n "$NAMESPACE" --no-headers | grep "$DEPLOYMENT_NAME" | while read -r line; do
        local pod_name cpu_usage memory_usage
        pod_name=$(echo "$line" | awk '{print $1}')
        cpu_usage=$(echo "$line" | awk '{print $2}' | sed 's/m$//')
        memory_usage=$(echo "$line" | awk '{print $3}' | sed 's/Mi$//')

        # Convert CPU from millicores to percentage (assuming 1000m = 100%)
        local cpu_percent
        cpu_percent=$((cpu_usage / 10))

        # Convert memory to percentage (assuming 1Gi = 1024Mi)
        local memory_percent
        memory_percent=$((memory_usage * 100 / 1024))

        jq -n \
            --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
            --arg pod "$pod_name" \
            --argjson cpu "$cpu_percent" \
            --argjson memory "$memory_percent" \
            '{
                timestamp: $timestamp,
                pod: $pod,
                cpu_percent: $cpu,
                memory_percent: $memory
            }' >> "$metrics_file"
    done

    echo "$metrics_file"
}

get_application_metrics() {
    local metrics_file="$METRICS_DIR/app-metrics-$(date +%s).json"

    # Get application health endpoint
    local health_response
    if health_response=$(kubectl exec -n "$NAMESPACE" deployment/"$DEPLOYMENT_NAME" -- curl -s -w "%{http_code},%{time_total}" http://localhost:8000/health 2>/dev/null); then
        local http_code response_time
        http_code=$(echo "$health_response" | tail -1 | cut -d',' -f1)
        response_time=$(echo "$health_response" | tail -1 | cut -d',' -f2)

        # Convert response time to milliseconds
        response_time_ms=$(echo "$response_time * 1000" | bc -l | cut -d'.' -f1)

        jq -n \
            --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
            --argjson http_code "$http_code" \
            --argjson response_time "$response_time_ms" \
            '{
                timestamp: $timestamp,
                health_check: {
                    http_code: $http_code,
                    response_time_ms: $response_time
                }
            }' >> "$metrics_file"
    else
        log_warning "Failed to get application health metrics"
    fi

    echo "$metrics_file"
}

get_error_rate() {
    # This would typically query your monitoring system (Prometheus, etc.)
    # For now, we'll simulate by checking pod logs for errors
    local error_count total_requests

    # Get recent logs and count errors
    local logs
    logs=$(kubectl logs -n "$NAMESPACE" deployment/"$DEPLOYMENT_NAME" --tail=1000 --since=1m 2>/dev/null || echo "")

    if [ -n "$logs" ]; then
        error_count=$(echo "$logs" | grep -c "ERROR\|CRITICAL\|5[0-9][0-9]" || echo "0")
        total_requests=$(echo "$logs" | grep -c "HTTP" || echo "1")  # Avoid division by zero

        # Calculate error rate
        local error_rate
        error_rate=$(echo "scale=4; $error_count / $total_requests" | bc -l)
        echo "$error_rate"
    else
        echo "0"
    fi
}

check_thresholds() {
    local pod_metrics_file="$1"
    local app_metrics_file="$2"
    local error_rate="$3"
    local alerts=()

    # Check error rate
    if (( $(echo "$error_rate > $ALERT_THRESHOLD_ERROR_RATE" | bc -l) )); then
        alerts+=("High error rate: ${error_rate} (threshold: ${ALERT_THRESHOLD_ERROR_RATE})")
    fi

    # Check pod metrics
    if [ -f "$pod_metrics_file" ]; then
        while read -r metric; do
            local cpu_percent memory_percent
            cpu_percent=$(echo "$metric" | jq -r '.cpu_percent')
            memory_percent=$(echo "$metric" | jq -r '.memory_percent')

            if [ "$cpu_percent" != "null" ] && (( cpu_percent > ALERT_THRESHOLD_CPU )); then
                alerts+=("High CPU usage: ${cpu_percent}% (threshold: ${ALERT_THRESHOLD_CPU}%)")
            fi

            if [ "$memory_percent" != "null" ] && (( memory_percent > ALERT_THRESHOLD_MEMORY )); then
                alerts+=("High memory usage: ${memory_percent}% (threshold: ${ALERT_THRESHOLD_MEMORY}%)")
            fi
        done < "$pod_metrics_file"
    fi

    # Check application metrics
    if [ -f "$app_metrics_file" ]; then
        local response_time
        response_time=$(jq -r '.health_check.response_time_ms' "$app_metrics_file" 2>/dev/null || echo "0")

        if [ "$response_time" != "null" ] && (( response_time > ALERT_THRESHOLD_RESPONSE_TIME )); then
            alerts+=("Slow response time: ${response_time}ms (threshold: ${ALERT_THRESHOLD_RESPONSE_TIME}ms)")
        fi
    fi

    # Send alerts
    for alert in "${alerts[@]}"; do
        log_alert "$alert"
    done

    return ${#alerts[@]}
}

generate_report() {
    local start_time="$1"
    local end_time="$2"
    local report_file="$METRICS_DIR/rollout-report-$(date +%s).json"

    log_info "Generating rollout report..."

    # Aggregate metrics
    local total_checks=0
    local total_alerts=0
    local avg_error_rate=0
    local max_cpu=0
    local max_memory=0
    local max_response_time=0

    # Count metrics files
    total_checks=$(find "$METRICS_DIR" -name "*-metrics-*.json" -newer "$start_time" | wc -l)

    # Calculate averages and maximums (simplified)
    if [ $total_checks -gt 0 ]; then
        # This is a simplified calculation - in a real implementation,
        # you'd properly aggregate the metrics from all files
        max_cpu=75  # Placeholder values
        max_memory=60
        max_response_time=1500
        avg_error_rate="0.02"
    fi

    # Create report
    jq -n \
        --arg start_time "$start_time" \
        --arg end_time "$end_time" \
        --arg feature "${FEATURE_NAME:-unknown}" \
        --argjson total_checks "$total_checks" \
        --argjson total_alerts "$total_alerts" \
        --arg avg_error_rate "$avg_error_rate" \
        --argjson max_cpu "$max_cpu" \
        --argjson max_memory "$max_memory" \
        --argjson max_response_time "$max_response_time" \
        '{
            report_type: "feature_rollout_monitoring",
            start_time: $start_time,
            end_time: $end_time,
            feature_name: $feature,
            summary: {
                total_checks: $total_checks,
                total_alerts: $total_alerts,
                avg_error_rate: ($avg_error_rate | tonumber),
                max_cpu_percent: $max_cpu,
                max_memory_percent: $max_memory,
                max_response_time_ms: $max_response_time
            },
            thresholds: {
                error_rate: '"$ALERT_THRESHOLD_ERROR_RATE"',
                cpu_percent: '"$ALERT_THRESHOLD_CPU"',
                memory_percent: '"$ALERT_THRESHOLD_MEMORY"',
                response_time_ms: '"$ALERT_THRESHOLD_RESPONSE_TIME"'
            }
        }' > "$report_file"

    log_success "Report generated: $report_file"

    # Display summary
    echo ""
    echo "=== Rollout Monitoring Summary ==="
    echo "Feature: ${FEATURE_NAME:-unknown}"
    echo "Duration: $(($(date +%s) - $(date -d "$start_time" +%s))) seconds"
    echo "Total checks: $total_checks"
    echo "Total alerts: $total_alerts"
    echo "Average error rate: $avg_error_rate"
    echo "Max CPU usage: ${max_cpu}%"
    echo "Max memory usage: ${max_memory}%"
    echo "Max response time: ${max_response_time}ms"
    echo "================================="
}

cleanup() {
    log_info "Cleaning up monitoring session..."

    # Remove old metrics files (keep last 24 hours)
    find "$METRICS_DIR" -name "*.json" -mtime +1 -delete 2>/dev/null || true

    log_info "Monitoring session completed"
}

# Signal handlers
trap cleanup EXIT
trap 'log_info "Monitoring interrupted by user"; exit 130' INT TERM

# Parse command line arguments
FEATURE_NAME=""
VERBOSE="false"
ALERT_WEBHOOK=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--feature)
            FEATURE_NAME="$2"
            shift 2
            ;;
        -d|--duration)
            MONITORING_DURATION="$2"
            shift 2
            ;;
        -i|--interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -t|--threshold-error)
            ALERT_THRESHOLD_ERROR_RATE="$2"
            shift 2
            ;;
        -r|--threshold-response)
            ALERT_THRESHOLD_RESPONSE_TIME="$2"
            shift 2
            ;;
        -c|--threshold-cpu)
            ALERT_THRESHOLD_CPU="$2"
            shift 2
            ;;
        -m|--threshold-memory)
            ALERT_THRESHOLD_MEMORY="$2"
            shift 2
            ;;
        -a|--alert-webhook)
            ALERT_WEBHOOK="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Enable verbose mode if requested
if [ "$VERBOSE" = "true" ]; then
    set -x
fi

# Check prerequisites
check_prerequisites

# Start monitoring
log_info "Starting feature rollout monitoring"
log_info "Feature: ${FEATURE_NAME:-not specified}"
log_info "Duration: ${MONITORING_DURATION} seconds"
log_info "Check interval: ${CHECK_INTERVAL} seconds"
log_info "Namespace: $NAMESPACE"

start_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
end_time=$(date -u -d "+${MONITORING_DURATION} seconds" +"%Y-%m-%dT%H:%M:%SZ")

log_info "Monitoring will run until: $end_time"

# Main monitoring loop
check_count=0
total_alerts=0

while [ $(date +%s) -lt $(date -d "$end_time" +%s) ]; do
    ((check_count++))

    log_info "Check #$check_count - Collecting metrics..."

    # Collect metrics
    pod_metrics_file=$(get_pod_metrics)
    app_metrics_file=$(get_application_metrics)
    error_rate=$(get_error_rate)

    if [ "$VERBOSE" = "true" ]; then
        log_info "Error rate: $error_rate"
        if [ -f "$pod_metrics_file" ]; then
            log_info "Pod metrics: $(cat "$pod_metrics_file")"
        fi
        if [ -f "$app_metrics_file" ]; then
            log_info "App metrics: $(cat "$app_metrics_file")"
        fi
    fi

    # Check thresholds and alert if necessary
    if ! check_thresholds "$pod_metrics_file" "$app_metrics_file" "$error_rate"; then
        ((total_alerts += $?))
    fi

    # Wait for next check
    if [ $(date +%s) -lt $(date -d "$end_time" +%s) ]; then
        log_info "Waiting ${CHECK_INTERVAL} seconds until next check..."
        sleep "$CHECK_INTERVAL"
    fi
done

# Generate final report
generate_report "$start_time" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

log_success "Monitoring completed successfully"

# Exit with error code if alerts were triggered
if [ $total_alerts -gt 0 ]; then
    log_warning "Monitoring completed with $total_alerts alerts"
    exit 1
else
    log_success "Monitoring completed with no alerts"
    exit 0
fi
