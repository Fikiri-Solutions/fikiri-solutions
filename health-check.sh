#!/bin/bash
# Automated Health Check Script
# Run this script every 5 minutes via cron: */5 * * * * /path/to/health-check.sh

set -e

# Configuration
BACKEND_URL="https://fikirisolutions.onrender.com"
FRONTEND_URL="https://fikirisolutions.vercel.app"
LOG_FILE="/tmp/fikiri-health.log"
ALERT_EMAIL="admin@fikirisolutions.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Alert function
alert() {
    local message="$1"
    log "🚨 ALERT: $message"
    # Send email alert (requires mail command)
    echo "$message" | mail -s "Fikiri Health Alert" "$ALERT_EMAIL" 2>/dev/null || true
}

# Check backend health
check_backend() {
    log "🔍 Checking backend health..."
    
    local response
    local status_code
    
    response=$(curl -fsSL -w "%{http_code}" "$BACKEND_URL/api/health" 2>/dev/null || echo "000")
    status_code="${response: -3}"
    
    if [ "$status_code" = "200" ]; then
        log "✅ Backend health check passed (HTTP $status_code)"
        
        # Check specific services
        local services_response
        services_response=$(curl -fsSL "$BACKEND_URL/api/health" 2>/dev/null)
        
        # Check if AI Assistant is healthy
        if echo "$services_response" | jq -e '.services.ai_assistant.status == "healthy"' >/dev/null 2>&1; then
            log "✅ AI Assistant service healthy"
        else
            alert "AI Assistant service unhealthy"
        fi
        
        # Check if CRM service is healthy
        if echo "$services_response" | jq -e '.services.crm.status == "healthy"' >/dev/null 2>&1; then
            log "✅ CRM service healthy"
        else
            alert "CRM service unhealthy"
        fi
        
        return 0
    else
        alert "Backend health check failed (HTTP $status_code)"
        return 1
    fi
}

# Check frontend availability
check_frontend() {
    log "🔍 Checking frontend availability..."
    
    local status_code
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" 2>/dev/null || echo "000")
    
    if [ "$status_code" = "200" ]; then
        log "✅ Frontend available (HTTP $status_code)"
        
        # Check if HTML content is non-empty
        local content_length
        content_length=$(curl -s -I "$FRONTEND_URL" | grep -i "content-length" | awk '{print $2}' | tr -d '\r\n')
        
        if [ -n "$content_length" ] && [ "$content_length" -gt 100 ]; then
            log "✅ Frontend content length: $content_length bytes"
        else
            alert "Frontend content too small: $content_length bytes"
        fi
        
        return 0
    else
        alert "Frontend unavailable (HTTP $status_code)"
        return 1
    fi
}

# Check API response time
check_performance() {
    log "🔍 Checking API performance..."
    
    local response_time
    response_time=$(curl -fsSL -w "%{time_total}" -o /dev/null "$BACKEND_URL/api/health" 2>/dev/null || echo "999")
    
    # Convert to milliseconds
    local response_ms
    response_ms=$(echo "$response_time * 1000" | bc)
    
    if (( $(echo "$response_ms < 400" | bc -l) )); then
        log "✅ API response time: ${response_ms}ms (within budget)"
    else
        alert "API response time too slow: ${response_ms}ms (budget: 400ms)"
    fi
}

# Check SSL certificate
check_ssl() {
    log "🔍 Checking SSL certificate..."
    
    local cert_expiry
    cert_expiry=$(echo | openssl s_client -servername fikirisolutions.com -connect fikirisolutions.com:443 2>/dev/null | openssl x509 -noout -dates | grep "notAfter" | cut -d= -f2)
    
    if [ -n "$cert_expiry" ]; then
        local expiry_timestamp
        expiry_timestamp=$(date -d "$cert_expiry" +%s)
        local current_timestamp
        current_timestamp=$(date +%s)
        local days_until_expiry
        days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [ "$days_until_expiry" -gt 30 ]; then
            log "✅ SSL certificate valid for $days_until_expiry days"
        else
            alert "SSL certificate expires in $days_until_expiry days"
        fi
    else
        alert "Could not check SSL certificate"
    fi
}

# Main health check
main() {
    log "🏥 Starting Fikiri Solutions health check..."
    
    local backend_healthy=0
    local frontend_healthy=0
    
    # Run checks
    check_backend && backend_healthy=1
    check_frontend && frontend_healthy=1
    check_performance
    check_ssl
    
    # Summary
    if [ "$backend_healthy" = 1 ] && [ "$frontend_healthy" = 1 ]; then
        log "🎉 All systems healthy!"
        exit 0
    else
        log "❌ Some systems unhealthy"
        exit 1
    fi
}

# Run main function
main "$@"
