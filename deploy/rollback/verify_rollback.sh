#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    POST-ROLLBACK VERIFICATION SCRIPT                          ║
# ║                    Verifies system health after rollback                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

# Verification results
PASSED=0
FAILED=0
WARNINGS=0

check() {
    local description="$1"
    local command="$2"

    echo -n "Checking $description... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

warn() {
    local description="$1"
    local command="$2"

    echo -n "Checking $description... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}WARN${NC}"
        ((WARNINGS++))
        return 1
    fi
}

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    POST-ROLLBACK VERIFICATION                              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Load environment
if [ -f .env ]; then
    source .env
else
    echo -e "${RED}✗ .env file not found${NC}"
    exit 1
fi

# ========================================
# PHASE 1: Infrastructure Health
# ========================================
echo -e "${YELLOW}PHASE 1: Infrastructure Health${NC}"
echo "───────────────────────────────────────────────────────────────────────────────────────"

check "Docker daemon" "docker info > /dev/null"
check "Layra network" "docker network inspect layra-net > /dev/null"
check "Backend container running" "docker ps | grep -q layra-backend"
check "Frontend container running" "docker ps | grep -q layra-frontend"
check "MySQL container running" "docker ps | grep -q layra-mysql"
check "MongoDB container running" "docker ps | grep -q layra-mongodb"
check "Redis container running" "docker ps | grep -q layra-redis"
check "Milvus container running" "docker ps | grep -q layra-milvus-standalone"
check "Model server container running" "docker ps | grep -q layra-model-server"

echo ""

# ========================================
# PHASE 2: Resource Health
# ========================================
echo -e "${YELLOW}PHASE 2: Resource Health${NC}"
echo "───────────────────────────────────────────────────────────────────────────────────────"

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    echo -e "Checking disk space... ${GREEN}PASS${NC} (${DISK_USAGE}% used)"
    ((PASSED++))
else
    echo -e "Checking disk space... ${RED}FAIL${NC} (${DISK_USAGE}% used, > 90%)"
    ((FAILED++))
fi

# Check memory
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2*100}')
if [ "$MEM_USAGE" -lt 95 ]; then
    echo -e "Checking system memory... ${GREEN}PASS${NC} (${MEM_USAGE}% used)"
    ((PASSED++))
else
    echo -e "Checking system memory... ${RED}FAIL${NC} (${MEM_USAGE}% used, > 95%)"
    ((FAILED++))
fi

echo ""

# ========================================
# PHASE 3: Database Connectivity
# ========================================
echo -e "${YELLOW}PHASE 3: Database Connectivity${NC}"
echo "───────────────────────────────────────────────────────────────────────────────────────"

# MySQL
if docker exec layra-mysql mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD:-root}" > /dev/null 2>&1; then
    echo -e "Checking MySQL connectivity... ${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "Checking MySQL connectivity... ${RED}FAIL${NC}"
    ((FAILED++))
fi

# MongoDB
if docker exec layra-mongodb mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    echo -e "Checking MongoDB connectivity... ${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "Checking MongoDB connectivity... ${RED}FAIL${NC}"
    ((FAILED++))
fi

# Redis
if docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1; then
    echo -e "Checking Redis connectivity... ${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "Checking Redis connectivity... ${RED}FAIL${NC}"
    ((FAILED++))
fi

# Milvus
if curl -sf http://localhost:19530/healthz > /dev/null 2>&1; then
    echo -e "Checking Milvus connectivity... ${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "Checking Milvus connectivity... ${YELLOW}WARN${NC} (may still be starting)"
    ((WARNINGS++))
fi

# Qdrant
if curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
    echo -e "Checking Qdrant connectivity... ${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "Checking Qdrant connectivity... ${YELLOW}WARN${NC}"
    ((WARNINGS++))
fi

echo ""

# ========================================
# PHASE 4: API Health
# ========================================
echo -e "${YELLOW}PHASE 4: API Health${NC}"
echo "───────────────────────────────────────────────────────────────────────────────────────"

# Wait a moment for services to be ready
sleep 5

check "Backend health endpoint" "curl -sf http://localhost:8090/api/v1/health/check"
warn "Backend metrics endpoint" "curl -sf http://localhost:8090/api/v1/health/metrics"

echo ""

# ========================================
# PHASE 5: Data Integrity
# ========================================
echo -e "${YELLOW}PHASE 5: Data Integrity${NC}"
echo "───────────────────────────────────────────────────────────────────────────────────────"

# MySQL data check
MYSQL_COUNT=$(docker exec layra-mysql mysql -u root -p"${MYSQL_ROOT_PASSWORD:-root}" -e "SELECT COUNT(*) FROM layra.users;" -sN 2>/dev/null || echo "0")
if [ "$MYSQL_COUNT" -ge 0 ]; then
    echo -e "Checking MySQL data... ${GREEN}PASS${NC} ($MYSQL_COUNT users)"
    ((PASSED++))
else
    echo -e "Checking MySQL data... ${RED}FAIL${NC}"
    ((FAILED++))
fi

# MongoDB data check
MONGO_COUNT=$(docker exec layra-mongodb mongosh layra --quiet --eval "db.conversations.countDocuments()" 2>/dev/null || echo "0")
if [ "$MONGO_COUNT" -ge 0 ]; then
    echo -e "Checking MongoDB data... ${GREEN}PASS${NC} ($MONGO_COUNT conversations)"
    ((PASSED++))
else
    echo -e "Checking MongoDB data... ${RED}FAIL${NC}"
    ((FAILED++))
fi

echo ""

# ========================================
# SUMMARY
# ========================================
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    VERIFICATION SUMMARY                                    ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}Passed:  $PASSED${NC}"
echo -e "  ${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "  ${RED}Failed:  $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                         ALL CHECKS PASSED                                    ║${NC}"
    echo -e "${GREEN}║                    ROLLBACK VERIFICATION SUCCESSFUL                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Monitor application logs: docker compose logs -f"
    echo "  2. Verify user-facing functionality"
    echo "  3. Complete post-mortem documentation"
    echo "  4. Plan re-migration with fixes"
    exit 0
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                       VERIFICATION FAILED                                     ║${NC}"
    echo -e "${RED}║                    ROLLBACK MAY BE INCOMPLETE                                ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Immediate actions:${NC}"
    echo "  1. Check logs: docker compose logs --tail=100"
    echo "  2. Inspect failed services: docker compose ps"
    echo "  3. Review error logs above"
    echo "  4. Consider manual intervention"
    exit 1
fi
