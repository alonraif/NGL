#!/bin/bash
#
# MySQL Migration Test Script
# Quick automated testing after migration
#

set -e

echo "==========================================="
echo "NGL MySQL Migration Test Suite"
echo "==========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

test_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Test 1: MySQL Service Running
echo "Test 1: MySQL service health"
if docker-compose ps mysql | grep -q "Up.*healthy"; then
    test_pass "MySQL service is running and healthy"
else
    test_fail "MySQL service is not healthy"
fi

# Test 2: Backend Service Running
echo "Test 2: Backend service health"
if docker-compose ps backend | grep -q "Up"; then
    test_pass "Backend service is running"
else
    test_fail "Backend service is not running"
fi

# Test 3: Database Connection
echo "Test 3: Database connection"
if docker-compose exec -T backend python -c "from database import engine; engine.connect()" 2>/dev/null; then
    test_pass "Backend can connect to MySQL"
else
    test_fail "Backend cannot connect to MySQL"
fi

# Test 4: Tables Exist
echo "Test 4: Database tables"
TABLE_COUNT=$(docker-compose exec -T mysql mysql -u ngl_user -pngl_password ngl_db -se "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'ngl_db';" 2>/dev/null)
if [ "$TABLE_COUNT" -ge 14 ]; then
    test_pass "All tables exist ($TABLE_COUNT tables found)"
else
    test_fail "Missing tables (only $TABLE_COUNT found, expected 14+)"
fi

# Test 5: Users Table
echo "Test 5: Users table"
USER_COUNT=$(docker-compose exec -T mysql mysql -u ngl_user -pngl_password ngl_db -se "SELECT COUNT(*) FROM users;" 2>/dev/null)
if [ "$USER_COUNT" -gt 0 ]; then
    test_pass "Users table populated ($USER_COUNT users)"
else
    test_fail "Users table is empty"
fi

# Test 6: Admin User Exists
echo "Test 6: Admin user"
ADMIN_EXISTS=$(docker-compose exec -T mysql mysql -u ngl_user -pngl_password ngl_db -se "SELECT COUNT(*) FROM users WHERE username='admin' AND role='admin';" 2>/dev/null)
if [ "$ADMIN_EXISTS" -eq 1 ]; then
    test_pass "Admin user exists"
else
    test_fail "Admin user not found"
fi

# Test 7: Parsers Table
echo "Test 7: Parsers table"
PARSER_COUNT=$(docker-compose exec -T mysql mysql -u ngl_user -pngl_password ngl_db -se "SELECT COUNT(*) FROM parsers;" 2>/dev/null)
if [ "$PARSER_COUNT" -gt 0 ]; then
    test_pass "Parsers table populated ($PARSER_COUNT parsers)"
else
    test_fail "Parsers table is empty"
fi

# Test 8: Health Endpoint
echo "Test 8: API health endpoint"
if curl -s http://localhost:5000/api/health | grep -q "healthy"; then
    test_pass "API health endpoint responding"
else
    test_fail "API health endpoint not responding"
fi

# Test 9: Login Endpoint
echo "Test 9: Login endpoint"
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"Admin123!"}' 2>/dev/null)

if echo "$LOGIN_RESPONSE" | grep -q "token"; then
    test_pass "Login endpoint working"
    # Extract token for further tests
    TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null || echo "")
else
    test_fail "Login endpoint failing"
    TOKEN=""
fi

# Test 10: Authenticated Request
if [ -n "$TOKEN" ]; then
    echo "Test 10: Authenticated request"
    ME_RESPONSE=$(curl -s http://localhost:5000/api/auth/me \
        -H "Authorization: Bearer $TOKEN" 2>/dev/null)

    if echo "$ME_RESPONSE" | grep -q "admin"; then
        test_pass "Authenticated requests working"
    else
        test_fail "Authenticated requests failing"
    fi
else
    echo "Test 10: Authenticated request"
    test_info "Skipped (no token from login)"
fi

# Test 11: Parse Modes Endpoint
if [ -n "$TOKEN" ]; then
    echo "Test 11: Parse modes endpoint"
    MODES_RESPONSE=$(curl -s http://localhost:5000/api/parse-modes \
        -H "Authorization: Bearer $TOKEN" 2>/dev/null)

    if echo "$MODES_RESPONSE" | grep -q "parse_modes"; then
        test_pass "Parse modes endpoint working"
    else
        test_fail "Parse modes endpoint failing"
    fi
else
    echo "Test 11: Parse modes endpoint"
    test_info "Skipped (no token from login)"
fi

# Test 12: Log Files Count
echo "Test 12: Log files"
LOG_COUNT=$(docker-compose exec -T mysql mysql -u ngl_user -pngl_password ngl_db -se "SELECT COUNT(*) FROM log_files WHERE is_deleted = 0;" 2>/dev/null)
test_info "Active log files: $LOG_COUNT"

# Test 13: Analyses Count
echo "Test 13: Analyses"
ANALYSIS_COUNT=$(docker-compose exec -T mysql mysql -u ngl_user -pngl_password ngl_db -se "SELECT COUNT(*) FROM analyses WHERE is_deleted = 0;" 2>/dev/null)
test_info "Active analyses: $ANALYSIS_COUNT"

# Test 14: Audit Log
echo "Test 14: Audit log"
AUDIT_COUNT=$(docker-compose exec -T mysql mysql -u ngl_user -pngl_password ngl_db -se "SELECT COUNT(*) FROM audit_log;" 2>/dev/null)
if [ "$AUDIT_COUNT" -gt 0 ]; then
    test_pass "Audit log populated ($AUDIT_COUNT entries)"
else
    test_info "Audit log is empty (might be new installation)"
fi

# Test 15: Celery Worker
echo "Test 15: Celery worker"
if docker-compose ps celery_worker | grep -q "Up"; then
    test_pass "Celery worker is running"
else
    test_fail "Celery worker is not running"
fi

# Test 16: Redis Connection
echo "Test 16: Redis connection"
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    test_pass "Redis is responding"
else
    test_fail "Redis is not responding"
fi

# Summary
echo ""
echo "==========================================="
echo "Test Results"
echo "==========================================="
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Test file upload via web interface"
    echo "  2. Verify analysis history is accessible"
    echo "  3. Check admin dashboard"
    echo "  4. Monitor logs: docker-compose logs -f backend"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check logs:${NC}"
    echo "  docker-compose logs backend"
    echo "  docker-compose logs mysql"
    exit 1
fi
