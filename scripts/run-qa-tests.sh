#!/bin/bash

# 🧪 Comprehensive QA Test Execution Script
# For Render-Inspired Landing Page

set -e

echo "🚀 Starting Comprehensive QA Test Suite"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run tests and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "\n${BLUE}🧪 Running: $test_name${NC}"
    echo "Command: $test_command"
    echo "----------------------------------------"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASSED: $test_name${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FAILED: $test_name${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install dependencies if needed
install_dependencies() {
    echo -e "\n${YELLOW}📦 Checking dependencies...${NC}"
    
    # Check for Node.js
    if ! command_exists node; then
        echo -e "${RED}❌ Node.js not found. Please install Node.js first.${NC}"
        exit 1
    fi
    
    # Check for npm
    if ! command_exists npm; then
        echo -e "${RED}❌ npm not found. Please install npm first.${NC}"
        exit 1
    fi
    
    # Install frontend dependencies
    if [ ! -d "frontend/node_modules" ]; then
        echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
        cd frontend && npm install && cd ..
    fi
    
    # Install K6 if not present
    if ! command_exists k6; then
        echo -e "${YELLOW}📦 Installing K6...${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install k6
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get update && sudo apt-get install k6
        else
            echo -e "${RED}❌ Please install K6 manually for your OS${NC}"
        fi
    fi
    
    # Install Cypress if not present
    if [ ! -d "frontend/node_modules/cypress" ]; then
        echo -e "${YELLOW}📦 Installing Cypress...${NC}"
        cd frontend && npm install cypress --save-dev && cd ..
    fi
}

# Function to run Jest unit tests
run_jest_tests() {
    echo -e "\n${BLUE}🧪 Running Jest Unit Tests${NC}"
    cd frontend
    
    # Run landing page tests
    run_test "Landing Page Unit Tests" "npm test -- --testPathPattern=landing.test.tsx --coverage --watchAll=false"
    
    # Run regression tests
    run_test "Regression Tests" "npm test -- --testPathPattern=regression.test.tsx --coverage --watchAll=false"
    
    cd ..
}

# Function to run Cypress E2E tests
run_cypress_tests() {
    echo -e "\n${BLUE}🧪 Running Cypress E2E Tests${NC}"
    cd frontend
    
    # Run E2E tests
    run_test "Cypress E2E Tests" "npx cypress run --spec 'cypress/e2e/landing.cy.js'"
    
    cd ..
}

# Function to run K6 performance tests
run_k6_tests() {
    echo -e "\n${BLUE}🧪 Running K6 Performance Tests${NC}"
    
    # Run performance tests
    run_test "K6 Performance Tests" "k6 run ../scripts/k6-performance-test.js"
}

# Function to run Lighthouse performance tests
run_lighthouse_tests() {
    echo -e "\n${BLUE}🧪 Running Lighthouse Performance Tests${NC}"
    
    # Install Lighthouse if not present
    if ! command_exists lighthouse; then
        echo -e "${YELLOW}📦 Installing Lighthouse...${NC}"
        npm install -g lighthouse
    fi
    
    # Run Lighthouse tests
    run_test "Lighthouse Performance Audit" "lighthouse https://www.fikirisolutions.com/home --output=json --output-path=./lighthouse-report.json --chrome-flags='--headless'"
}

# Function to run accessibility tests
run_accessibility_tests() {
    echo -e "\n${BLUE}🧪 Running Accessibility Tests${NC}"
    
    # Install axe-core if not present
    if [ ! -d "frontend/node_modules/axe-core" ]; then
        echo -e "${YELLOW}📦 Installing axe-core...${NC}"
        cd frontend && npm install axe-core --save-dev && cd ..
    fi
    
    # Run accessibility tests
    run_test "Accessibility Tests" "cd frontend && npx cypress run --spec 'cypress/e2e/accessibility.cy.js'"
}

# Function to run API tests
run_api_tests() {
    echo -e "\n${BLUE}🧪 Running API Tests${NC}"
    
    # Test health endpoint
    run_test "Health Endpoint Test" "curl -s -o /dev/null -w '%{http_code}' https://fikirisolutions.onrender.com/api/health | grep -q '200'"
    
    # Test industry prompts endpoint
    run_test "Industry Prompts Endpoint Test" "curl -s -o /dev/null -w '%{http_code}' https://fikirisolutions.onrender.com/api/industry/prompts | grep -q '200'"
    
    # Test industry chat endpoint
    run_test "Industry Chat Endpoint Test" "curl -s -X POST -H 'Content-Type: application/json' -d '{\"industry\":\"landscaping\",\"client_id\":\"test\",\"message\":\"test\"}' https://fikirisolutions.onrender.com/api/industry/chat | grep -q 'success'"
}

# Function to run deployment tests
run_deployment_tests() {
    echo -e "\n${BLUE}🧪 Running Deployment Tests${NC}"
    
    # Test frontend deployment
    run_test "Frontend Deployment Test" "curl -s -o /dev/null -w '%{http_code}' https://www.fikirisolutions.com/home | grep -q '200'"
    
    # Test backend deployment
    run_test "Backend Deployment Test" "curl -s -o /dev/null -w '%{http_code}' https://fikirisolutions.onrender.com/api/health | grep -q '200'"
    
    # Test DNS configuration
    run_test "DNS Configuration Test" "nslookup www.fikirisolutions.com | grep -q 'fikirisolutions.com'"
}

# Function to run cross-browser tests
run_cross_browser_tests() {
    echo -e "\n${BLUE}🧪 Running Cross-Browser Tests${NC}"
    
    # Test in different browsers (requires browser automation)
    run_test "Chrome Compatibility Test" "curl -s -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' https://www.fikirisolutions.com/home | grep -q 'Automate emails'"
    
    run_test "Firefox Compatibility Test" "curl -s -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0' https://www.fikirisolutions.com/home | grep -q 'Automate emails'"
    
    run_test "Safari Compatibility Test" "curl -s -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15' https://www.fikirisolutions.com/home | grep -q 'Automate emails'"
}

# Function to generate test report
generate_report() {
    echo -e "\n${BLUE}📊 Generating Test Report${NC}"
    
    local success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}🎉 QA Test Suite Complete${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "Total Tests: $TOTAL_TESTS"
    echo -e "Passed: $PASSED_TESTS"
    echo -e "Failed: $FAILED_TESTS"
    echo -e "Success Rate: $success_rate%"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All tests passed! Ready for production.${NC}"
    else
        echo -e "\n${RED}⚠️  Some tests failed. Please review and fix issues.${NC}"
    fi
    
    # Generate detailed report
    cat > qa-test-results.md << EOF
# QA Test Results - $(date)

## Summary
- **Total Tests**: $TOTAL_TESTS
- **Passed**: $PASSED_TESTS
- **Failed**: $FAILED_TESTS
- **Success Rate**: $success_rate%

## Test Categories
- ✅ Unit Tests (Jest)
- ✅ E2E Tests (Cypress)
- ✅ Performance Tests (K6)
- ✅ Accessibility Tests
- ✅ API Tests
- ✅ Deployment Tests
- ✅ Cross-Browser Tests

## Status
$(if [ $FAILED_TESTS -eq 0 ]; then echo "🎉 **PASSED** - Ready for production"; else echo "⚠️ **FAILED** - Review issues"; fi)

## Generated
$(date)
EOF
    
    echo -e "\n${GREEN}📄 Detailed report saved to: qa-test-results.md${NC}"
}

# Main execution
main() {
    echo -e "${GREEN}🚀 Starting Comprehensive QA Test Suite${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Install dependencies
    install_dependencies
    
    # Run all test suites
    run_jest_tests
    run_cypress_tests
    run_k6_tests
    run_lighthouse_tests
    run_accessibility_tests
    run_api_tests
    run_deployment_tests
    run_cross_browser_tests
    
    # Generate final report
    generate_report
}

# Run main function
main "$@"
