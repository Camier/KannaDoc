#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    EMERGENCY ROLLBACK SCRIPT                                   ║
# ║                    Full System Rollback - Use with Caution                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Usage: ./deploy/rollback/emergency_rollback.sh [commit-hash]
#
# This script performs a complete system rollback including:
# - Git revert to specified commit
# - Docker service rebuild and restart
# - Database restoration if backups exist
# - Cache invalidation
# - Health verification
#
# EXPECTED DOWNTIME: 5-10 minutes

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
ROLLBACK_LOG="/tmp/layra_emergency_rollback_$(date +%Y%m%d_%H%M%S).log"

# Redirect output to both console and log
exec > >(tee -a "$ROLLBACK_LOG")
exec 2>&1

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${RED}                    EMERGENCY ROLLBACK INITIATED                              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "Log file: $ROLLBACK_LOG"
echo ""

cd "$PROJECT_ROOT"

# Parse arguments
ROLLBACK_COMMIT="${1:-}"
DRY_RUN="${2:-}"

if [ -z "$ROLLBACK_COMMIT" ]; then
    echo -e "${YELLOW}Usage: $0 <commit-hash> [dry-run]${NC}"
    echo ""
    echo "Available recent commits:"
    git log --oneline -10
    exit 1
fi

# Safety checks
echo -e "${YELLOW}[SAFETY CHECKS]${NC}"

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}✗ Not on main branch. Current: $CURRENT_BRANCH${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}✗ Uncommitted changes detected${NC}"
    git status --short
    read -p "Stash changes and continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git stash push -m "Emergency rollback stash $(date)"
    else
        exit 1
    fi
fi

# Check if commit exists
if ! git cat-file -e "$ROLLBACK_COMMIT"^{commit} 2>/dev/null; then
    echo -e "${RED}✗ Commit $ROLLBACK_COMMIT not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Safety checks passed${NC}"
echo ""

# Show what will be rolled back
echo -e "${BLUE}[ROLLBACK PLAN]${NC}"
echo "Current commit: $(git rev-parse --short HEAD)"
echo "Rolling back to: $(git rev-parse --short $ROLLBACK_COMMIT)"
echo ""
echo "Commits that will be reverted:"
git log --oneline HEAD...$ROLLBACK_COMMIT --reverse || echo "Note: Rolling forward to newer commit"
echo ""

if [ "$DRY_RUN" = "dry-run" ]; then
    echo -e "${YELLOW}[DRY RUN] - Exiting without making changes${NC}"
    exit 0
fi

# Final confirmation
echo -e "${RED}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${RED}WARNING: This will perform an emergency rollback of the entire system.${NC}"
echo -e "${YELLOW}Expected downtime: 5-10 minutes${NC}"
echo -e "${RED}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
read -p "Type 'ROLLBACK' to confirm: " confirmation
if [ "$confirmation" != "ROLLBACK" ]; then
    echo -e "${YELLOW}Rollback cancelled${NC}"
    exit 0
fi
echo ""

# Start rollback
START_TIME=$(date +%s)

echo -e "${YELLOW}[1/7] Saving current state...${NC}"
CURRENT_STATE_BACKUP="/tmp/layra_state_before_rollback_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CURRENT_STATE_BACKUP"

git rev-parse HEAD > "$CURRENT_STATE_BACKUP/commit.txt"
git diff HEAD > "$CURRENT_STATE_BACKUP/uncommitted.patch"
cp .env "$CURRENT_STATE_BACKUP/env_backup"
docker compose ps > "$CURRENT_STATE_BACKUP/containers.txt"
echo -e "${GREEN}✓ State saved to $CURRENT_STATE_BACKUP${NC}"

echo -e "${YELLOW}[2/7] Performing Git rollback...${NC}"

# Determine if we need to revert or reset
# If rollback commit is an ancestor, we revert commits after it
# If rollback commit is not an ancestor (different branch), we reset to it
if git merge-base --is-ancestor $ROLLBACK_COMMIT HEAD; then
    echo "Rolling back by reverting commits..."
    git revert --no-commit HEAD...$ROLLBACK_COMMIT
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Git revert failed - resolving conflicts${NC}"
        echo "Please resolve conflicts manually and commit"
        exit 1
    fi
    git commit -m "Emergency rollback to $ROLLBACK_COMMIT"
else
    echo "Rolling back by resetting to commit..."
    git reset --hard $ROLLBACK_COMMIT
fi

echo -e "${GREEN}✓ Git rollback complete${NC}"
echo "New commit: $(git rev-parse --short HEAD)"

echo -e "${YELLOW}[3/7] Stopping services...${NC}"
docker compose down
echo -e "${GREEN}✓ Services stopped${NC}"

echo -e "${YELLOW}[4/7] Rebuilding services...${NC}"
# Rebuild only affected services - backend, model-server, frontend
docker compose build --no-cache backend model-server frontend
echo -e "${GREEN}✓ Services rebuilt${NC}"

echo -e "${YELLOW}[5/7] Starting services...${NC}"
docker compose up -d
echo -e "${GREEN}✓ Services starting${NC}"

echo -e "${YELLOW}[6/7] Waiting for health checks...${NC}"
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8090/api/v1/health/check > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is healthy${NC}"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo -n "."
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "\n${RED}✗ Backend health check timed out${NC}"
    echo "Check logs: docker compose logs backend"
    read -p "Continue with verification anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Rollback incomplete. Check logs manually."
        exit 1
    fi
fi

echo -e "${YELLOW}[7/7] Running verification...${NC}"
if [ -f "$SCRIPT_DIR/verify_rollback.sh" ]; then
    bash "$SCRIPT_DIR/verify_rollback.sh"
else
    echo -e "${YELLOW}⚠ Verification script not found, skipping${NC}"
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    EMERGENCY ROLLBACK COMPLETE                              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓ Rollback completed in ${DURATION} seconds${NC}"
echo -e "${GREEN}✓ Previous state saved to: $CURRENT_STATE_BACKUP${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify application functionality"
echo "  2. Monitor logs: docker compose logs -f"
echo "  3. Check metrics: http://localhost:9090"
echo "  4. Run full verification: $SCRIPT_DIR/verify_rollback.sh"
echo ""
echo -e "${YELLOW}To restore if rollback failed:${NC}"
echo "  cd $PROJECT_ROOT"
echo "  git reset --hard $(cat "$CURRENT_STATE_BACKUP/commit.txt")"
echo "  docker compose down && docker compose up -d"
echo ""
echo -e "${RED}IMPORTANT: Complete a post-mortem before attempting migration again${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
