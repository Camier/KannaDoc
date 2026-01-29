#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    PRE-MIGRATION BACKUP SCRIPT                                ║
# ║                    Complete system backup before migration                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Usage: ./deploy/scripts/backup.sh [output-directory]
#
# Creates complete backup including:
# - Git state
# - All databases
# - Vector DB volumes
# - Configuration files
# - Container state

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEFAULT_BACKUP_ROOT="/tmp/layra_backups"
BACKUP_DIR="${1:-${DEFAULT_BACKUP_ROOT}/pre_migration_${TIMESTAMP}}"

mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    PRE-MIGRATION BACKUP                                      ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Backup directory: $BACKUP_DIR"
echo "Started at: $(date)"
echo ""

# Load environment
if [ -f .env ]; then
    source .env
else
    echo -e "${YELLOW}⚠ .env file not found, some backups may fail${NC}"
fi

# ========================================
# 1. Git State
# ========================================
echo -e "${YELLOW}[1/8] Backing up Git state...${NC}"

git rev-parse HEAD > "$BACKUP_DIR/git_commit.txt"
git log --oneline -10 > "$BACKUP_DIR/git_recent_commits.txt"
git diff HEAD > "$BACKUP_DIR/git_uncommitted.patch" 2>/dev/null || true
git status --short > "$BACKUP_DIR/git_status.txt"

echo -e "${GREEN}✓ Git state backed up${NC}"

# ========================================
# 2. Configuration Files
# ========================================
echo -e "${YELLOW}[2/8] Backing up configuration...${NC}"

cp .env "$BACKUP_DIR/env_backup" 2>/dev/null || true
cp docker-compose.yml "$BACKUP_DIR/docker-compose_backup.yml" 2>/dev/null || true
cp -f .env.example "$BACKUP_DIR/env_example_backup" 2>/dev/null || true

echo -e "${GREEN}✓ Configuration backed up${NC}"

# ========================================
# 3. Container State
# ========================================
echo -e "${YELLOW}[3/8] Recording container state...${NC}"

docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" > "$BACKUP_DIR/containers_running.txt"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}" > "$BACKUP_DIR/images.txt"
docker volume ls > "$BACKUP_DIR/volumes.txt"

echo -e "${GREEN}✓ Container state recorded${NC}"

# ========================================
# 4. MySQL Backup
# ========================================
echo -e "${YELLOW}[4/8] Backing up MySQL...${NC}"

if docker ps | grep -q "layra-mysql.*Up"; then
    docker exec layra-mysql mysqldump \
        -u root -p"${MYSQL_ROOT_PASSWORD:-root}" \
        --all-databases \
        --single-transaction \
        --quick \
        --lock-tables=false \
        > "$BACKUP_DIR/mysql_full.sql" 2>/dev/null

    if [ $? -eq 0 ] && [ -s "$BACKUP_DIR/mysql_full.sql" ]; then
        echo -e "${GREEN}✓ MySQL backed up ($(du -h "$BACKUP_DIR/mysql_full.sql" | cut -f1))${NC}"
    else
        echo -e "${YELLOW}⚠ MySQL backup failed or empty${NC}"
    fi
else
    echo -e "${YELLOW}⚠ MySQL container not running, skipping${NC}"
fi

# ========================================
# 5. MongoDB Backup
# ========================================
echo -e "${YELLOW}[5/8] Backing up MongoDB...${NC}"

if docker ps | grep -q "layra-mongodb.*Up"; then
    docker exec layra-mongodb mongodump \
        --username "${MONGODB_ROOT_USERNAME:-root}" \
        --password "${MONGODB_ROOT_PASSWORD}" \
        --authenticationDatabase admin \
        --out /tmp/mongo_backup \
        > /dev/null 2>&1

    docker cp layra-mongodb:/tmp/mongo_backup "$BACKUP_DIR/mongo_dump"
    docker exec layra-mongodb rm -rf /tmp/mongo_backup

    if [ -d "$BACKUP_DIR/mongo_dump" ]; then
        echo -e "${GREEN}✓ MongoDB backed up ($(du -sh "$BACKUP_DIR/mongo_dump" | cut -f1))${NC}"
    else
        echo -e "${YELLOW}⚠ MongoDB backup failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ MongoDB container not running, skipping${NC}"
fi

# ========================================
# 6. Redis Backup
# ========================================
echo -e "${YELLOW}[6/8] Backing up Redis...${NC}"

if docker ps | grep -q "layra-redis.*Up"; then
    docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" save > /dev/null 2>&1
    docker cp layra-redis:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb"

    if [ -f "$BACKUP_DIR/redis_dump.rdb" ]; then
        echo -e "${GREEN}✓ Redis backed up ($(du -h "$BACKUP_DIR/redis_dump.rdb" | cut -f1))${NC}"
    else
        echo -e "${YELLOW}⚠ Redis backup failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Redis container not running, skipping${NC}"
fi

# ========================================
# 7. Vector Database Volumes
# ========================================
echo -e "${YELLOW}[7/8] Backing up vector databases...${NC}"

# Milvus
if docker volume ls | grep -q "layra_milvus_data"; then
    docker run --rm \
        -v layra_milvus_data:/data \
        -v "$BACKUP_DIR:/backup" \
        alpine tar czf "/backup/milvus_data.tar.gz" -C /data . 2>/dev/null

    if [ -f "$BACKUP_DIR/milvus_data.tar.gz" ]; then
        echo -e "${GREEN}✓ Milvus data backed up ($(du -h "$BACKUP_DIR/milvus_data.tar.gz" | cut -f1))${NC}"
    else
        echo -e "${YELLOW}⚠ Milvus backup failed${NC}"
    fi
fi

# Qdrant
if docker volume ls | grep -q "layra_qdrant_data"; then
    docker run --rm \
        -v layra_qdrant_data:/data \
        -v "$BACKUP_DIR:/backup" \
        alpine tar czf "/backup/qdrant_data.tar.gz" -C /data . 2>/dev/null

    if [ -f "$BACKUP_DIR/qdrant_data.tar.gz" ]; then
        echo -e "${GREEN}✓ Qdrant data backed up ($(du -h "$BACKUP_DIR/qdrant_data.tar.gz" | cut -f1))${NC}"
    else
        echo -e "${YELLOW}⚠ Qdrant backup failed${NC}"
    fi
fi

# ========================================
# 8. Metadata
# ========================================
echo -e "${YELLOW}[8/8] Creating backup metadata...${NC}"

cat > "$BACKUP_DIR/info.txt" << EOF
Layra Pre-Migration Backup
==========================
Timestamp: $TIMESTAMP
Date: $(date)
Hostname: $(hostname)
User: $(whoami)
Git Commit: $(git rev-parse --short HEAD)
Git Branch: $(git branch --show-current)

Backup Contents:
EOF

du -sh "$BACKUP_DIR"/* >> "$BACKUP_DIR/info.txt"

echo -e "${GREEN}✓ Metadata created${NC}"

# ========================================
# Complete
# ========================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    BACKUP COMPLETE                                          ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓ Backup saved to: $BACKUP_DIR${NC}"
echo -e "${GREEN}✓ Total size: $(du -sh "$BACKUP_DIR" | cut -f1)${NC}"
echo ""
echo -e "${YELLOW}To restore from this backup:${NC}"
echo "  ./deploy/rollback/emergency_rollback.sh $(cat "$BACKUP_DIR/git_commit.txt")"
echo ""
echo -e "${YELLOW}To restore database specifically:${NC}"
echo "  ./deploy/rollback/db_rollback.sh mysql $BACKUP_DIR/mysql_full.sql"
echo "  ./deploy/rollback/db_rollback.sh mongodb $BACKUP_DIR/mongo_dump"
echo ""
echo -e "${YELLOW}Backup contents:${NC}"
ls -lh "$BACKUP_DIR"
echo ""
