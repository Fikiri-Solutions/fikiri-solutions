#!/usr/bin/env bash
# Automated Smoke Test for Fikiri Solutions Authentication System
# Run this after each deploy to ensure nothing has broken

set -e  # Exit on any error

# Configuration
BASE_URL=${BASE_URL:-"http://localhost:5000/api/auth"}
TEST_EMAIL=${TEST_EMAIL:-"test@example.com"}
TEST_PASSWORD=${TEST_PASSWORD:-"test123"}
COOKIES_FILE="smoke_test_cookies.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    rm -f "$COOKIES_FILE"
}
trap cleanup EXIT

echo -e "${YELLOW}🔍 Fikiri Solutions Smoke Test: $(date)${NC}"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}1. Testing Backend Health...${NC}"
if curl -fsSL "http://localhost:5000/" -w "Status: %{http_code}\n" -o /dev/null; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    exit 1
fi

# Test 2: Whoami Endpoint
echo -e "${YELLOW}2. Testing Whoami Endpoint...${NC}"
WHOAMI_RESPONSE=$(curl -fsSL "$BASE_URL/whoami" -H "Content-Type: application/json")
if echo "$WHOAMI_RESPONSE" | grep -q '"success": true'; then
    echo -e "${GREEN}✅ Whoami endpoint working${NC}"
else
    echo -e "${RED}❌ Whoami endpoint failed${NC}"
    echo "Response: $WHOAMI_RESPONSE"
    exit 1
fi

# Test 3: Login Endpoint
echo -e "${YELLOW}3. Testing Login Endpoint...${NC}"
LOGIN_RESPONSE=$(curl -fsSL -X POST "$BASE_URL/login" \
    -H "Content-Type: application/json" \
    -H "Origin: https://fikirisolutions.com" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" \
    -c "$COOKIES_FILE" -b "$COOKIES_FILE")

if echo "$LOGIN_RESPONSE" | grep -q '"success": true'; then
    echo -e "${GREEN}✅ Login endpoint working${NC}"
    
    # Extract access token
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null)
    
    if [ ! -z "$ACCESS_TOKEN" ]; then
        echo -e "${GREEN}✅ Access token generated successfully${NC}"
    else
        echo -e "${RED}❌ No access token received${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Login endpoint failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

# Test 4: Token Verification
echo -e "${YELLOW}4. Testing Token Verification...${NC}"
TOKEN_TEST=$(curl -fsSL "$BASE_URL/whoami" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json")

if echo "$TOKEN_TEST" | grep -q '"authenticated": true'; then
    echo -e "${GREEN}✅ Token verification working${NC}"
else
    echo -e "${RED}❌ Token verification failed${NC}"
    echo "Response: $TOKEN_TEST"
    exit 1
fi

# Test 5: Cookie Security
echo -e "${YELLOW}5. Testing Cookie Security...${NC}"
COOKIE_TEST=$(curl -fsSL -X POST "$BASE_URL/login" \
    -H "Content-Type: application/json" \
    -H "Origin: https://fikirisolutions.com" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}" \
    -v 2>&1 | grep "Set-Cookie")

if echo "$COOKIE_TEST" | grep -q "Secure" && echo "$COOKIE_TEST" | grep -q "HttpOnly" && echo "$COOKIE_TEST" | grep -q "SameSite=None"; then
    echo -e "${GREEN}✅ Cookie security flags correct${NC}"
else
    echo -e "${RED}❌ Cookie security flags missing${NC}"
    echo "Cookie: $COOKIE_TEST"
    exit 1
fi

# Test 6: CORS Configuration
echo -e "${YELLOW}6. Testing CORS Configuration...${NC}"
CORS_TEST=$(curl -fsSL -X OPTIONS "$BASE_URL/login" \
    -H "Origin: https://fikirisolutions.com" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: Content-Type" \
    -w "%{http_code}")

if echo "$CORS_TEST" | grep -q "200"; then
    echo -e "${GREEN}✅ CORS preflight working${NC}"
else
    echo -e "${RED}❌ CORS preflight failed${NC}"
    exit 1
fi

# Test 7: Database Connection
echo -e "${YELLOW}7. Testing Database Connection...${NC}"
DB_TEST=$(python3 -c "
from core.database_optimization import db_optimizer
try:
    result = db_optimizer.execute_query('SELECT COUNT(*) as count FROM users')
    print(f'SUCCESS: {result[0][\"count\"]} users')
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)
")

if echo "$DB_TEST" | grep -q "SUCCESS"; then
    echo -e "${GREEN}✅ Database connection working${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
    echo "Error: $DB_TEST"
    exit 1
fi

# Test 8: Redis Connection
echo -e "${YELLOW}8. Testing Redis Connection...${NC}"
REDIS_TEST=$(python3 -c "
import redis
import os
from dotenv import load_dotenv
load_dotenv()

redis_url = os.getenv('REDIS_URL')
try:
    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    print('SUCCESS: Redis connected')
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)
")

if echo "$REDIS_TEST" | grep -q "SUCCESS"; then
    echo -e "${GREEN}✅ Redis connection working${NC}"
else
    echo -e "${RED}❌ Redis connection failed${NC}"
    echo "Error: $REDIS_TEST"
    exit 1
fi

# Test 9: Frontend (if running locally)
echo -e "${YELLOW}9. Testing Frontend...${NC}"
if curl -fsSL "http://localhost:5173/" -o /dev/null 2>/dev/null; then
    echo -e "${GREEN}✅ Frontend serving successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend not running locally (expected in production)${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}🎉 ALL SMOKE TESTS PASSED!${NC}"
echo -e "${GREEN}System is stable and ready for production.${NC}"
echo ""
echo "Test Summary:"
echo "✅ Backend Health Check"
echo "✅ Authentication Endpoints"
echo "✅ Token Generation & Verification"
echo "✅ Cookie Security"
echo "✅ CORS Configuration"
echo "✅ Database Connection"
echo "✅ Redis Connection"
echo "✅ Frontend (if running)"

# Cleanup
cleanup

echo ""
echo -e "${YELLOW}Smoke test completed successfully at $(date)${NC}"
