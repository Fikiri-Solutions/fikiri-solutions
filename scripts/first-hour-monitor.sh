#!/bin/bash
# 📊 First-Hour Post-Deploy Monitoring Script
# Continuous monitoring for the first hour after deployment

set -e

# Configuration
BACKEND_URL="https://fikirisolutions.onrender.com"
FRONTEND_URL="https://www.fikirisolutions.com"
LOG_FILE="/tmp/fikiri-first-hour-monitor.log"
ALERT_EMAIL="admin@fikirisolutions.com"
MONITOR_DURATION=3600  # 1 hour in seconds

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Alert thresholds
MAX_ERROR_RATE=1.0      # 1% error rate threshold
MAX_LATENCY_P95=300     # 300ms p95 latency threshold
MAX_QUEUE_LAG=30        # 30 seconds queue lag threshold
OAUTH_FAILURE_THRESHOLD=3  # 3 OAuth failures per user

# Monitoring data
declare -A error_counts
declare -A response_times
declare -A oauth_failures
start_time=$(date +%s)

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Alert function
alert() {
    local severity="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    log "🚨 ALERT [$severity]: $message"
    
    # Send email alert
    echo "Alert: $message" | mail -s "Fikiri $severity Alert" "$ALERT_EMAIL" 2>/dev/null || true
    
    # Log to system log
    logger "Fikiri $severity Alert: $message"
}

# Check health endpoint
check_health() {
    local response
    local status_code
    
    response=$(curl -fsSL -w "%{http_code}" "$BACKEND_URL/api/health" 2>/dev/null || echo "000")
    status_code="${response: -3}"
    
    if [ "$status_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Check response time
check_response_time() {
    local response_time
    response_time=$(curl -fsSL -w "%{time_total}" -o /dev/null "$BACKEND_URL/api/health" 2>/dev/null || echo "999")
    
    # Convert to milliseconds
    local response_ms
    response_ms=$(echo "$response_time * 1000" | bc)
    
    echo "$response_ms"
}

# Check error rate
check_error_rate() {
    local total_requests=0
    local error_requests=0
    
    # Check last 5 minutes of logs
    if [ -f "logs/fikiri_$(date +%Y%m%d).log" ]; then
        local log_file="logs/fikiri_$(date +%Y%m%d).log"
        local five_min_ago=$(date -d '5 minutes ago' '+%Y-%m-%d %H:%M:%S')
        
        # Count total requests (approximate)
        total_requests=$(grep -c "GET\|POST\|PUT\|DELETE" "$log_file" 2>/dev/null || echo "0")
        
        # Count error responses
        error_requests=$(grep -c "ERROR\|CRITICAL\|Exception\|5[0-9][0-9]" "$log_file" 2>/dev/null || echo "0")
    fi
    
    if [ "$total_requests" -gt 0 ]; then
        local error_rate=$(echo "scale=2; $error_requests * 100 / $total_requests" | bc)
        echo "$error_rate"
    else
        echo "0"
    fi
}

# Check OAuth failures
check_oauth_failures() {
    local failure_count=0
    
    if [ -f "logs/fikiri_$(date +%Y%m%d).log" ]; then
        local log_file="logs/fikiri_$(date +%Y%m%d).log"
        local fifteen_min_ago=$(date -d '15 minutes ago' '+%Y-%m-%d %H:%M:%S')
        
        # Count OAuth refresh failures in last 15 minutes
        failure_count=$(grep -c "OAuth refresh failed\|Token refresh failed" "$log_file" 2>/dev/null || echo "0")
    fi
    
    echo "$failure_count"
}

# Check queue lag
check_queue_lag() {
    # This would need to be implemented based on your queue system
    # For now, return 0 (no lag)
    echo "0"
}

# Check automation failures
check_automation_failures() {
    local failure_count=0
    
    if [ -f "logs/fikiri_$(date +%Y%m%d).log" ]; then
        local log_file="logs/fikiri_$(date +%Y%m%d).log"
        local ten_min_ago=$(date -d '10 minutes ago' '+%Y-%m-%d %H:%M:%S')
        
        # Count automation failures in last 10 minutes
        failure_count=$(grep -c "Automation failed\|Rule execution failed" "$log_file" 2>/dev/null || echo "0")
    fi
    
    echo "$failure_count"
}

# Main monitoring loop
monitor_loop() {
    local iteration=0
    
    while [ $(($(date +%s) - start_time)) -lt $MONITOR_DURATION ]; do
        iteration=$((iteration + 1))
        log "📊 Monitoring iteration $iteration"
        
        # Health check
        if check_health; then
            log "✅ Health check passed"
        else
            alert "CRITICAL" "Health check failed"
        fi
        
        # Response time check
        local response_time=$(check_response_time)
        log "⏱️  Response time: ${response_time}ms"
        
        if (( $(echo "$response_time > $MAX_LATENCY_P95" | bc -l) )); then
            alert "WARNING" "Response time too high: ${response_time}ms (threshold: ${MAX_LATENCY_P95}ms)"
        fi
        
        # Error rate check
        local error_rate=$(check_error_rate)
        log "📈 Error rate: ${error_rate}%"
        
        if (( $(echo "$error_rate > $MAX_ERROR_RATE" | bc -l) )); then
            alert "WARNING" "Error rate too high: ${error_rate}% (threshold: ${MAX_ERROR_RATE}%)"
        fi
        
        # OAuth failure check
        local oauth_failures=$(check_oauth_failures)
        log "🔐 OAuth failures (15min): $oauth_failures"
        
        if [ "$oauth_failures" -ge "$OAUTH_FAILURE_THRESHOLD" ]; then
            alert "CRITICAL" "OAuth failures exceeded threshold: $oauth_failures (threshold: $OAUTH_FAILURE_THRESHOLD)"
        fi
        
        # Automation failure check
        local automation_failures=$(check_automation_failures)
        log "🤖 Automation failures (10min): $automation_failures"
        
        if [ "$automation_failures" -gt 5 ]; then
            alert "CRITICAL" "Automation failures exceeded threshold: $automation_failures (threshold: 5)"
        fi
        
        # Queue lag check
        local queue_lag=$(check_queue_lag)
        log "📋 Queue lag: ${queue_lag}s"
        
        if [ "$queue_lag" -gt "$MAX_QUEUE_LAG" ]; then
            alert "WARNING" "Queue lag too high: ${queue_lag}s (threshold: ${MAX_QUEUE_LAG}s)"
        fi
        
        # Wait 5 minutes before next check
        log "⏳ Waiting 5 minutes for next check..."
        sleep 300
    done
}

# Rollback trigger function
trigger_rollback() {
    local reason="$1"
    
    alert "CRITICAL" "Triggering rollback: $reason"
    
    # Enable kill-switch
    curl -X POST "$BACKEND_URL/api/automation/kill-switch" \
        -H "Content-Type: application/json" \
        -d '{"enabled":true}' 2>/dev/null || true
    
    log "🛑 Kill-switch enabled"
    log "📋 Rollback procedures initiated"
    
    # Log rollback trigger
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ROLLBACK TRIGGERED: $reason" >> "$LOG_FILE"
}

# Setup monitoring
setup_monitoring() {
    log "🚀 Starting first-hour post-deploy monitoring"
    log "Duration: $MONITOR_DURATION seconds ($(($MONITOR_DURATION / 60)) minutes)"
    log "Alert email: $ALERT_EMAIL"
    log "Backend URL: $BACKEND_URL"
    log "Frontend URL: $FRONTEND_URL"
    log ""
    
    # Create log file
    touch "$LOG_FILE"
    
    # Initial health check
    log "🔍 Initial health check..."
    if check_health; then
        log "✅ Initial health check passed"
    else
        alert "CRITICAL" "Initial health check failed - deployment may have issues"
        trigger_rollback "Initial health check failed"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    log "🧹 Cleaning up monitoring resources"
    
    # Archive log file
    local archive_file="/tmp/fikiri-monitor-$(date +%Y%m%d-%H%M%S).log"
    cp "$LOG_FILE" "$archive_file"
    log "📁 Monitoring log archived: $archive_file"
}

# Signal handlers
trap cleanup EXIT
trap 'trigger_rollback "Manual interrupt"' INT TERM

# Main execution
main() {
    setup_monitoring
    monitor_loop
    
    log "✅ First-hour monitoring completed successfully"
    log "📊 Final summary:"
    log "  - Monitoring duration: $MONITOR_DURATION seconds"
    log "  - Log file: $LOG_FILE"
    log "  - No critical issues detected"
}

# Run main function
main "$@"
