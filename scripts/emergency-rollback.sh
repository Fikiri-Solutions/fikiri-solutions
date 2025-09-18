#!/bin/bash
# 🧭 Emergency Rollback Script for Fikiri v1.0.0
# One-screen rollback instructions for production issues

set -e

# Configuration
BACKEND_URL="https://fikirisolutions.onrender.com"
FRONTEND_URL="https://www.fikirisolutions.com"
LOG_FILE="/tmp/fikiri-rollback.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Alert function
alert() {
    local message="$1"
    log "🚨 ROLLBACK ALERT: $message"
    echo -e "${RED}🚨 $message${NC}"
}

# Success function
success() {
    local message="$1"
    log "✅ SUCCESS: $message"
    echo -e "${GREEN}✅ $message${NC}"
}

# Warning function
warning() {
    local message="$1"
    log "⚠️  WARNING: $message"
    echo -e "${YELLOW}⚠️  $message${NC}"
}

# Step 1: Enable Kill-Switch
enable_kill_switch() {
    echo -e "${BLUE}🛑 STEP 1: ENABLING KILL-SWITCH${NC}"
    echo "=================================="
    
    log "Enabling global kill-switch to pause all outbound actions..."
    
    local response
    response=$(curl -sS -X POST "$BACKEND_URL/api/automation/kill-switch" \
        -H "Content-Type: application/json" \
        -d '{"enabled":true}' 2>/dev/null || echo '{"success":false}')
    
    if echo "$response" | jq -e '.success == true' >/dev/null 2>&1; then
        success "Kill-switch enabled - all automations paused"
        
        # Verify kill-switch is enabled
        local status_response
        status_response=$(curl -sS "$BACKEND_URL/api/automation/safety-status" 2>/dev/null || echo '{}')
        
        if echo "$status_response" | jq -e '.data.global_kill_switch_enabled == true' >/dev/null 2>&1; then
            success "Kill-switch status verified"
        else
            warning "Kill-switch status verification failed"
        fi
    else
        alert "Failed to enable kill-switch - manual intervention required"
        return 1
    fi
    
    echo ""
}

# Step 2: Re-deploy Last Good Release
redeploy_last_good_release() {
    echo -e "${BLUE}🔄 STEP 2: RE-DEPLOYING LAST GOOD RELEASE${NC}"
    echo "============================================="
    
    # Get last good release tag
    local last_good_tag
    last_good_tag=$(git tag -l | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -2 | head -1)
    
    if [ -z "$last_good_tag" ]; then
        alert "No previous release tag found"
        return 1
    fi
    
    log "Reverting to release: $last_good_tag"
    
    # Checkout last good release
    if git checkout "$last_good_tag" >/dev/null 2>&1; then
        success "Checked out release: $last_good_tag"
    else
        alert "Failed to checkout release: $last_good_tag"
        return 1
    fi
    
    # Force push to main branch
    if git push origin main --force >/dev/null 2>&1; then
        success "Force pushed $last_good_tag to main branch"
    else
        alert "Failed to force push to main branch"
        return 1
    fi
    
    # Restart backend services
    log "Restarting backend services..."
    if command -v pm2 >/dev/null 2>&1; then
        pm2 restart all >/dev/null 2>&1 && success "Backend services restarted" || warning "Backend restart may have failed"
    else
        warning "PM2 not found - manual service restart required"
    fi
    
    echo ""
}

# Step 3: Database Migration Rollback
rollback_database_migration() {
    echo -e "${BLUE}🗄️  STEP 3: DATABASE MIGRATION ROLLBACK${NC}"
    echo "====================================="
    
    # Check if there are any recent migrations
    local migration_files
    migration_files=$(find scripts/migrations -name "*.py" -type f 2>/dev/null | sort | tail -1)
    
    if [ -n "$migration_files" ]; then
        log "Found recent migration: $migration_files"
        
        # Run migration rollback
        if python "$migration_files" down >/dev/null 2>&1; then
            success "Database migration rolled back"
        else
            warning "Migration rollback may have failed"
        fi
    else
        log "No recent migrations found to rollback"
    fi
    
    # Alternative: Restore from backup
    local backup_file
    backup_file="data/fikiri_backup_$(date +%Y%m%d).db"
    
    if [ -f "$backup_file" ]; then
        log "Found backup file: $backup_file"
        
        if cp "$backup_file" "data/fikiri.db" >/dev/null 2>&1; then
            success "Database restored from backup"
        else
            warning "Database restore may have failed"
        fi
    else
        warning "No backup file found for today"
    fi
    
    echo ""
}

# Step 4: Clear Vercel Build Cache
clear_vercel_cache() {
    echo -e "${BLUE}🌐 STEP 4: CLEARING VERCEL BUILD CACHE${NC}"
    echo "======================================="
    
    log "Clearing Vercel build cache..."
    
    # Clear build cache and redeploy frontend
    if command -v vercel >/dev/null 2>&1; then
        if vercel --prod --force >/dev/null 2>&1; then
            success "Vercel build cache cleared and frontend redeployed"
        else
            warning "Vercel cache clear may have failed"
        fi
    else
        warning "Vercel CLI not found - manual cache clear required"
        log "Manual steps:"
        log "1. Go to Vercel dashboard"
        log "2. Select your project"
        log "3. Go to Settings > Functions"
        log "4. Click 'Clear Build Cache'"
        log "5. Redeploy the project"
    fi
    
    echo ""
}

# Step 5: Verify Rollback
verify_rollback() {
    echo -e "${BLUE}✅ STEP 5: VERIFYING ROLLBACK${NC}"
    echo "============================="
    
    log "Running smoke tests to verify rollback..."
    
    # Wait for services to stabilize
    sleep 30
    
    # Test health endpoint
    if curl -fsSL "$BACKEND_URL/api/health" >/dev/null 2>&1; then
        success "Backend health check passed"
    else
        alert "Backend health check failed"
        return 1
    fi
    
    # Test frontend
    if curl -fsSL "$FRONTEND_URL" >/dev/null 2>&1; then
        success "Frontend health check passed"
    else
        alert "Frontend health check failed"
        return 1
    fi
    
    # Test kill-switch status
    local kill_switch_status
    kill_switch_status=$(curl -sS "$BACKEND_URL/api/automation/safety-status" 2>/dev/null || echo '{}')
    
    if echo "$kill_switch_status" | jq -e '.data.global_kill_switch_enabled == true' >/dev/null 2>&1; then
        success "Kill-switch still enabled (as expected)"
    else
        warning "Kill-switch status unclear"
    fi
    
    echo ""
}

# Step 6: Disable Kill-Switch
disable_kill_switch() {
    echo -e "${BLUE}🔓 STEP 6: DISABLING KILL-SWITCH${NC}"
    echo "=================================="
    
    log "Disabling kill-switch to resume normal operations..."
    
    local response
    response=$(curl -sS -X POST "$BACKEND_URL/api/automation/kill-switch" \
        -H "Content-Type: application/json" \
        -d '{"enabled":false}' 2>/dev/null || echo '{"success":false}')
    
    if echo "$response" | jq -e '.success == true' >/dev/null 2>&1; then
        success "Kill-switch disabled - automations resumed"
        
        # Verify kill-switch is disabled
        local status_response
        status_response=$(curl -sS "$BACKEND_URL/api/automation/safety-status" 2>/dev/null || echo '{}')
        
        if echo "$status_response" | jq -e '.data.global_kill_switch_enabled == false' >/dev/null 2>&1; then
            success "Kill-switch status verified as disabled"
        else
            warning "Kill-switch status verification failed"
        fi
    else
        alert "Failed to disable kill-switch"
        return 1
    fi
    
    echo ""
}

# Emergency procedures
emergency_procedures() {
    echo -e "${RED}🚨 EMERGENCY PROCEDURES${NC}"
    echo "====================="
    echo ""
    echo "If automated rollback fails:"
    echo ""
    echo "1. Manual Kill-Switch:"
    echo "   curl -X POST $BACKEND_URL/api/automation/kill-switch \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"enabled\":true}'"
    echo ""
    echo "2. Manual Database Restore:"
    echo "   cp data/fikiri_backup_$(date +%Y%m%d).db data/fikiri.db"
    echo ""
    echo "3. Manual Service Restart:"
    echo "   pm2 restart all"
    echo ""
    echo "4. Manual Frontend Rollback:"
    echo "   vercel rollback"
    echo ""
    echo "5. Contact Information:"
    echo "   - Primary: DevOps Team"
    echo "   - Secondary: Development Team"
    echo "   - Escalation: CTO"
    echo ""
}

# Main rollback function
main_rollback() {
    echo -e "${RED}🧭 FIKIRI EMERGENCY ROLLBACK PROCEDURE${NC}"
    echo "============================================="
    echo ""
    echo "This script will perform a complete rollback to the last known good state."
    echo "All outbound automations will be paused during the rollback."
    echo ""
    
    # Confirm rollback
    read -p "Are you sure you want to proceed with rollback? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Rollback cancelled."
        exit 0
    fi
    
    echo ""
    log "Starting emergency rollback procedure"
    
    # Execute rollback steps
    enable_kill_switch || exit 1
    redeploy_last_good_release || exit 1
    rollback_database_migration || exit 1
    clear_vercel_cache || exit 1
    verify_rollback || exit 1
    disable_kill_switch || exit 1
    
    echo ""
    success "🎉 ROLLBACK COMPLETED SUCCESSFULLY!"
    echo ""
    echo "Next steps:"
    echo "1. Monitor system for 30 minutes"
    echo "2. Run smoke tests: ./scripts/smoke-tests.sh"
    echo "3. Check logs for any remaining issues"
    echo "4. Notify team of rollback completion"
    echo ""
    
    log "Rollback completed successfully"
}

# Show help
show_help() {
    echo "Fikiri Emergency Rollback Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --emergency, -e     Show emergency procedures only"
    echo "  --kill-switch, -k   Only toggle kill-switch"
    echo "  --verify, -v        Only verify current state"
    echo ""
    echo "Examples:"
    echo "  $0                  # Full rollback procedure"
    echo "  $0 --emergency     # Show emergency procedures"
    echo "  $0 --kill-switch   # Toggle kill-switch only"
    echo ""
}

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --emergency|-e)
        emergency_procedures
        exit 0
        ;;
    --kill-switch|-k)
        enable_kill_switch
        exit 0
        ;;
    --verify|-v)
        verify_rollback
        exit 0
        ;;
    "")
        main_rollback
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
