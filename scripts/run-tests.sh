#!/bin/bash

# Comprehensive Test Runner for Fikiri Solutions
# This script runs all types of tests and provides detailed reporting

echo "🧪 FIKIRI SOLUTIONS - COMPREHENSIVE TEST SUITE"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to run tests with error handling
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${BLUE}Running: $test_name${NC}"
    echo "Command: $test_command"
    echo ""
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ $test_name PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name FAILED${NC}"
        return 1
    fi
}

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 1. TypeScript Type Checking
echo -e "${YELLOW}1. TYPESCRIPT TYPE CHECKING${NC}"
echo "================================"
if run_test "TypeScript Type Check" "cd frontend && npm run type-check"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))
echo ""

# 2. ESLint Code Quality
echo -e "${YELLOW}2. CODE QUALITY (ESLINT)${NC}"
echo "=========================="
if run_test "ESLint Code Quality" "cd frontend && npm run lint"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))
echo ""

# 3. Unit Tests
echo -e "${YELLOW}3. UNIT TESTS${NC}"
echo "============="
if run_test "Unit Tests" "cd frontend && npm test -- src/__tests__/crm-unit.test.ts --run"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))
echo ""

# 4. Build Test
echo -e "${YELLOW}4. BUILD TEST${NC}"
echo "============="
if run_test "Frontend Build" "cd frontend && npm run build"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))
echo ""

# 5. Backend Health Check
echo -e "${YELLOW}5. BACKEND HEALTH CHECK${NC}"
echo "======================"
if run_test "Backend Health Check" "curl -s https://fikirisolutions.onrender.com/api/health | jq -r '.status' | grep -q 'healthy'"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))
echo ""

# 6. Frontend Deployment Check
echo -e "${YELLOW}6. FRONTEND DEPLOYMENT CHECK${NC}"
echo "============================="
if run_test "Frontend Deployment" "curl -s https://fikirisolutions.com | grep -q 'index-'"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))
echo ""

# 7. CRM API Endpoint Test
echo -e "${YELLOW}7. CRM API ENDPOINT TEST${NC}"
echo "========================="
if run_test "CRM API Endpoint" "curl -s https://fikirisolutions.onrender.com/api/crm/leads | jq -r '.success' | grep -q 'true'"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))
echo ""

# Test Summary
echo -e "${YELLOW}TEST SUMMARY${NC}"
echo "============"
echo -e "Total Tests: ${BLUE}$TOTAL_TESTS${NC}"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! 🎉${NC}"
    echo -e "${GREEN}✅ Code is ready for production${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}⚠️  Please fix the failing tests before deployment${NC}"
    exit 1
fi
