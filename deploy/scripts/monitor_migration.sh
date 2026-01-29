#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    MIGRATION MONITORING SCRIPT                                ║
# ║                    Real-time monitoring during migration                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Usage: ./deploy/scripts/monitor_migration.sh
#
# Monitors critical metrics during migration:
# - API health and response times
# - Error rates
# - Resource usage
# - Database connectivity
# - Container health

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

# Configuration
HEALTH_URL="http://localhost:8090/api/v1/health/check"
METRICS_URL="http://localhost:8090/api/v1/health/metrics"
CHECK_INTERVAL=5
ALERT_THRESHOLD_ERROR_RATE=10
ALERT_THRESHOLD_LATENCY=2000  # ms

# Statistics
TOTAL_CHECKS=0
FAILED_CHECKS=0
HIGH_ERROR_COUNT=0

# Alert function
alert() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        CRITICAL)
            echo -e "${RED}[${timestamp}] CRITICAL: $message${NC}"
            ;;
        WARNING)
            echo -e "${YELLOW}[${timestamp}] WARNING: $message${NC}"
            ;;
        INFO)
            echo -e "${BLUE}[${timestamp}] INFO: $message${NC}"
            ;;
        *)
            echo "[${timestamp}] $message"
            ;;
    esac
}

# Health check function
check_health() {
    local response=$(curl -s -w "\n%{http_code}" "$HEALTH_URL" 2>/dev/null)
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo "UP"
        return 0
    else
        echo "DOWN"
        return 1
    fi
}

# Latency check function
check_latency() {
    local start=$(date +%s%3N)
    curl -sf "$HEALTH_URL" > /dev/null 2>&1
    local end=$(date +%s%3N)
    local latency=$((end - start))
    echo "$latency"
}

# Error rate check (from logs)
check_error_rate() {
    local error_count=$(docker compose logs --since=1m backend 2>&1 | grep -i "error\|exception\|5.." | wc -l)
    local total_requests=$(docker compose logs --since=1m backend 2>&1 | wc -l)

    if [ "$total_requests" -gt 0 ]; then
        local rate=$((error_count * 100 / total_requests))
        echo "$rate"
    else
        echo "0"
    fi
}

# Resource check
check_resources() {
    local cpu=$(docker stats --no-stream --format "{{.CPUPerc}}" layra-backend | sed 's/%//')
    local mem=$(docker stats --no-stream --format "{{.MemPerc}}" layra-backend | sed 's/%//')

    echo "CPU: ${cpu}% | MEM: ${mem}%"
}

# Database check
check_databases() {
    local mysql_up=0
    local mongo_up=0
    local redis_up=0

    if docker exec layra-mysql mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD:-root}" > /dev/null 2>&1; then
        mysql_up=1
    fi

    if docker exec layra-mongodb mongosh --quiet --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        mongo_up=1
    fi

    if docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1; then
        redis_up=1
    fi

    echo "MySQL: $mysql_up | Mongo: $mongo_up | Redis: $redis_up"
}

# Clear screen and show header
show_header() {
    clear
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                    MIGRATION MONITOR                                        ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo "Started: $(date)"
    echo "Press Ctrl+C to stop monitoring"
    echo ""
}

# Main monitoring loop
main() {
    show_header

    # Initial health check
    alert INFO "Starting migration monitoring..."
    sleep 2

    while true; do
        ((TOTAL_CHECKS++))

        # Health check
        health_status=$(check_health)
        health_result=$?

        if [ $health_result -eq 0 ]; then
            health_display="${GREEN}UP${NC}"
        else
            health_display="${RED}DOWN${NC}"
            ((FAILED_CHECKS++))
            alert CRITICAL "Health check failed!"
        fi

        # Latency check
        latency=$(check_latency)
        if [ "$latency" -gt "$ALERT_THRESHOLD_LATENCY" ]; then
            latency_display="${RED}${latency}ms${NC}"
            alert WARNING "High latency detected: ${latency}ms"
        else
            latency_display="${GREEN}${latency}ms${NC}"
        fi

        # Error rate check
        error_rate=$(check_error_rate)
        if [ "$error_rate" -gt "$ALERT_THRESHOLD_ERROR_RATE" ]; then
            error_display="${RED}${error_rate}%${NC}"
            ((HIGH_ERROR_COUNT++))
            alert CRITICAL "High error rate: ${error_rate}%"
        else
            error_display="${GREEN}${error_rate}%${NC}"
        fi

        # Resources
        resources=$(check_resources)

        # Databases
        databases=$(check_databases)

        # Display status
        echo -ne "\r\033[K"
        echo -e "Check #${TOTAL_CHECKS} | Health: ${health_display} | Latency: ${latency_display} | Errors: ${error_display} | ${resources} | ${databases}"

        # Sleep before next check
        sleep $CHECK_INTERVAL
    done
}

# Trap to show summary on exit
trap 'show_summary; exit 0' INT TERM

show_summary() {
    echo ""
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                    MONITORING SUMMARY                                       ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Total checks: $TOTAL_CHECKS"
    echo "Failed checks: $FAILED_CHECKS"
    echo "High error rate incidents: $HIGH_ERROR_COUNT"
    echo ""

    if [ $FAILED_CHECKS -eq 0 ] && [ $HIGH_ERROR_COUNT -eq 0 ]; then
        echo -e "${GREEN}✓ Migration appears stable - no critical issues detected${NC}"
    elif [ $FAILED_CHECKS -gt 0 ]; then
        echo -e "${RED}✗ Multiple health check failures detected - consider rollback${NC}"
    fi

    if [ $HIGH_ERROR_COUNT -gt 5 ]; then
        echo -e "${RED}✗ High error rate detected multiple times - recommend investigation${NC}"
    fi

    echo ""
    echo "For detailed logs:"
    echo "  docker compose logs backend --tail=100"
    echo ""
    echo "To initiate rollback:"
    echo "  ./deploy/rollback/emergency_rollback.sh <commit-hash>"
}

# Run main function
main
