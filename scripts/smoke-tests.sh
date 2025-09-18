#!/bin/bash
# 🧪 15-Minute Smoke Test Script for Fikiri v1.0.0
# Copy-paste ready smoke tests for post-deployment validation

set -e

# Configuration - REPLACE <TOKEN> with a fresh user JWT
BASE="https://fikirisolutions.onrender.com"
FRONT="https://www.fikirisolutions.com"
AUTH="Authorization: Bearer <TOKEN>"
JSON='Content-Type: application/json'

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_status="$3"
    
    echo -e "${BLUE}🔍 Testing: $test_name${NC}"
    
    if eval "$command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED: $test_name${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED: $test_name${NC}"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Header
echo -e "${BLUE}🧪 Starting Fikiri v1.0.0 Smoke Tests${NC}"
echo "=============================================="
echo ""

# 1) Health Check
echo -e "${YELLOW}1. HEALTH CHECK${NC}"
echo "---------------"
run_test "Backend Health" "curl -sS '$BASE/api/health' | jq -e '.status == \"healthy\"'"

# Check service map
echo -e "${BLUE}🔍 Checking service map...${NC}"
health_response=$(curl -sS "$BASE/api/health")
if echo "$health_response" | jq -e '.services | length > 0' >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Service map populated${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Service map empty${NC}"
    ((TESTS_FAILED++))
fi
echo ""

# 2) OAuth Status + Safety Endpoints
echo -e "${YELLOW}2. OAUTH & SAFETY ENDPOINTS${NC}"
echo "-------------------------------"

# Note: These require authentication, so we'll test endpoint availability
run_test "OAuth Token Status Endpoint" "curl -sS -H '$AUTH' '$BASE/api/oauth/token-status'"
run_test "Automation Safety Status Endpoint" "curl -sS -H '$AUTH' '$BASE/api/automation/safety-status'"

# 3) Onboarding Flow
echo -e "${YELLOW}3. ONBOARDING FLOW${NC}"
echo "-------------------"

# Test onboarding endpoints
run_test "Start Onboarding Job" "curl -sS -X POST -H '$AUTH' '$BASE/api/onboarding/start'"
run_test "Onboarding Status" "curl -sS -H '$AUTH' '$BASE/api/onboarding/status'"

# Check if onboarding progresses to COMPLETED
echo -e "${BLUE}🔍 Checking onboarding progression...${NC}"
onboarding_status=$(curl -sS -H "$AUTH" "$BASE/api/onboarding/status")
if echo "$onboarding_status" | jq -e '.data.status == "COMPLETED"' >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Onboarding completed${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠️  Onboarding in progress or not started${NC}"
fi
echo ""

# 4) Leads + Metrics
echo -e "${YELLOW}4. LEADS & METRICS${NC}"
echo "-------------------"

# Test leads endpoint
run_test "Leads Endpoint" "curl -sS -H '$AUTH' '$BASE/api/leads'"

# Check leads count
echo -e "${BLUE}🔍 Checking leads count...${NC}"
leads_response=$(curl -sS -H "$AUTH" "$BASE/api/leads")
leads_count=$(echo "$leads_response" | jq -r 'length // 0')
if [ "$leads_count" -ge 1 ]; then
    echo -e "${GREEN}✅ Leads count ≥ 1: $leads_count${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ No leads found: $leads_count${NC}"
    ((TESTS_FAILED++))
fi

# Test metrics endpoint
run_test "Metrics Summary" "curl -sS -H '$AUTH' '$BASE/api/metrics/summary'"
echo ""

# 5) Rate Limit Guard
echo -e "${YELLOW}5. RATE LIMIT GUARD${NC}"
echo "-------------------"

echo -e "${BLUE}🔍 Testing rate limits (65 requests)...${NC}"
rate_limit_test_passed=false
rate_limit_429_count=0

for i in {1..65}; do
    status_code=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" "$BASE/api/leads")
    if [ "$status_code" = "429" ]; then
        ((rate_limit_429_count++))
    fi
done

if [ "$rate_limit_429_count" -gt 0 ]; then
    echo -e "${GREEN}✅ Rate limiting working: $rate_limit_429_count 429 responses${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Rate limiting not working: 0 429 responses${NC}"
    ((TESTS_FAILED++))
fi
echo ""

# 6) Kill-Switch Test
echo -e "${YELLOW}6. KILL-SWITCH TEST${NC}"
echo "-------------------"

# Toggle kill-switch ON
echo -e "${BLUE}🔍 Toggling kill-switch ON...${NC}"
kill_switch_on=$(curl -sS -X POST -H "$AUTH" -H "$JSON" -d '{"enabled":true}' "$BASE/api/automation/kill-switch")
if echo "$kill_switch_on" | jq -e '.success == true' >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Kill-switch enabled${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Failed to enable kill-switch${NC}"
    ((TESTS_FAILED++))
fi

# Check safety status
echo -e "${BLUE}🔍 Checking safety status...${NC}"
safety_status=$(curl -sS -H "$AUTH" "$BASE/api/automation/safety-status")
if echo "$safety_status" | jq -e '.data.global_kill_switch_enabled == true' >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Kill-switch status confirmed${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Kill-switch status not confirmed${NC}"
    ((TESTS_FAILED++))
fi

# Toggle kill-switch OFF
echo -e "${BLUE}🔍 Toggling kill-switch OFF...${NC}"
kill_switch_off=$(curl -sS -X POST -H "$AUTH" -H "$JSON" -d '{"enabled":false}' "$BASE/api/automation/kill-switch")
if echo "$kill_switch_off" | jq -e '.success == true' >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Kill-switch disabled${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Failed to disable kill-switch${NC}"
    ((TESTS_FAILED++))
fi
echo ""

# Frontend Tests
echo -e "${YELLOW}7. FRONTEND TESTS${NC}"
echo "-------------------"

run_test "Frontend Homepage" "curl -sS '$FRONT'"
run_test "Frontend Dashboard" "curl -sS '$FRONT/dashboard'"
run_test "Frontend AI Assistant" "curl -sS '$FRONT/ai'"
run_test "Frontend CRM" "curl -sS '$FRONT/crm'"
run_test "Frontend Services" "curl -sS '$FRONT/services'"
run_test "Frontend Login" "curl -sS '$FRONT/login'"
run_test "Frontend Onboarding" "curl -sS '$FRONT/onboarding'"

# Performance Tests
echo -e "${YELLOW}8. PERFORMANCE TESTS${NC}"
echo "----------------------"

# Test response times
echo -e "${BLUE}🔍 Testing response times...${NC}"
response_time=$(curl -sS -w "%{time_total}" -o /dev/null "$BASE/api/health")
response_ms=$(echo "$response_time * 1000" | bc)

if (( $(echo "$response_ms < 300" | bc -l) )); then
    echo -e "${GREEN}✅ Response time: ${response_ms}ms (within budget)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Response time too slow: ${response_ms}ms (budget: 300ms)${NC}"
    ((TESTS_FAILED++))
fi
echo ""

# Summary
echo -e "${BLUE}📊 SMOKE TEST SUMMARY${NC}"
echo "========================"
echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL SMOKE TESTS PASSED!${NC}"
    echo -e "${GREEN}✅ System is ready for production use${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME SMOKE TESTS FAILED${NC}"
    echo -e "${RED}⚠️  Review failed tests before proceeding${NC}"
    exit 1
fi
