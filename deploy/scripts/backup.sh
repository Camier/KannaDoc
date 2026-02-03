#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    LAYRA DATA BACKUP SCRIPT                                  ║
# ║                    Complete system backup for all data volumes               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Usage: ./deploy/scripts/backup.sh [output-directory]
#
# Creates complete backup including:
# - Git commit hash
# - MySQL dump
# - MongoDB dump
# - Redis RDB save
# - MinIO volume snapshot
# - Milvus (Data, MinIO, Etcd) volume snapshots

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEFAULT_BACKUP_ROOT="/tmp/layra_backups"
BACKUP_DIR="${1:-${DEFAULT_BACKUP_ROOT}/backup_${TIMESTAMP}}"

mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    LAYRA SYSTEM BACKUP                                       ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "Backup directory: $BACKUP_DIR"
echo "Started at: $(date)"
echo ""

# Load environment
if [ -f .env ]; then
    # Use a subshell to avoid polluting current shell but export variables
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${YELLOW}⚠ .env file not found, using default credentials${NC}"
fi

# ========================================
# 1. Git State
# ========================================
echo -e "${YELLOW}[1/7] Recording Git state...${NC}"
git rev-parse HEAD > "$BACKUP_DIR/git_commit.txt"
git log --oneline -1 > "$BACKUP_DIR/git_info.txt"
echo -e "${GREEN}✓ Git commit recorded: $(cat "$BACKUP_DIR/git_commit.txt" | cut -c1-7)${NC}"

# ========================================
# 2. MySQL Backup
# ========================================
echo -e "${YELLOW}[2/7] Backing up MySQL (layra-mysql)...${NC}"
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
        echo -e "${RED}✗ MySQL backup failed or empty${NC}"
    fi
else
    echo -e "${YELLOW}⚠ MySQL container not running, attempting volume backup...${NC}"
    docker run --rm -v layra_mysql_data:/data -v "$BACKUP_DIR:/backup" alpine tar czf "/backup/mysql_data_vol.tar.gz" -C /data . 2>/dev/null
    echo -e "${GREEN}✓ MySQL volume backed up${NC}"
fi

# ========================================
# 3. MongoDB Backup
# ========================================
echo -e "${YELLOW}[3/7] Backing up MongoDB (layra-mongodb)...${NC}"
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
        echo -e "${RED}✗ MongoDB backup failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ MongoDB container not running, attempting volume backup...${NC}"
    docker run --rm -v layra_mongo_data:/data -v "$BACKUP_DIR:/backup" alpine tar czf "/backup/mongo_data_vol.tar.gz" -C /data . 2>/dev/null
    echo -e "${GREEN}✓ MongoDB volume backed up${NC}"
fi

# ========================================
# 4. Redis Backup
# ========================================
echo -e "${YELLOW}[4/7] Backing up Redis (layra-redis)...${NC}"
if docker ps | grep -q "layra-redis.*Up"; then
    docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" save > /dev/null 2>&1
    docker cp layra-redis:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb"

    if [ -f "$BACKUP_DIR/redis_dump.rdb" ]; then
        echo -e "${GREEN}✓ Redis backed up ($(du -h "$BACKUP_DIR/redis_dump.rdb" | cut -f1))${NC}"
    else
        echo -e "${RED}✗ Redis backup failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Redis container not running, attempting volume backup...${NC}"
    docker run --rm -v layra_redis_data:/data -v "$BACKUP_DIR:/backup" alpine tar czf "/backup/redis_data_vol.tar.gz" -C /data . 2>/dev/null
    echo -e "${GREEN}✓ Redis volume backed up${NC}"
fi

# ========================================
# 5. MinIO Backup
# ========================================
echo -e "${YELLOW}[5/7] Backing up MinIO data (layra_minio_data)...${NC}"
if docker volume ls | grep -q "layra_minio_data"; then
    docker run --rm \
        -v layra_minio_data:/data \
        -v "$BACKUP_DIR:/backup" \
        alpine tar czf "/backup/minio_data.tar.gz" -C /data . 2>/dev/null
    echo -e "${GREEN}✓ MinIO data volume backed up${NC}"
else
    echo -e "${RED}✗ MinIO volume layra_minio_data not found${NC}"
fi

# ========================================
# 6. Milvus Backup
# ========================================
echo -e "${YELLOW}[6/7] Backing up Milvus stack (Data, MinIO, Etcd)...${NC}"
MILVUS_VOLUMES=("layra_milvus_data" "layra_milvus_minio" "layra_milvus_etcd")
for vol in "${MILVUS_VOLUMES[@]}"; do
    if docker volume ls | grep -q "$vol"; then
        echo -e "  - Backing up $vol..."
        docker run --rm \
            -v "$vol":/data \
            -v "$BACKUP_DIR:/backup" \
            alpine tar czf "/backup/${vol}.tar.gz" -C /data . 2>/dev/null
    fi
done
echo -e "${GREEN}✓ Milvus stack backed up${NC}"

# ========================================
# 7. Metadata
# ========================================
echo -e "${YELLOW}[7/7] Finalizing backup metadata...${NC}"
cat > "$BACKUP_DIR/backup_info.json" << EOF
{
  "project": "LAYRA",
  "timestamp": "$TIMESTAMP",
  "date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "git_commit": "$(git rev-parse HEAD)",
  "host": "$(hostname)",
  "contents": [
    "mysql_full.sql",
    "mongo_dump",
    "redis_dump.rdb",
    "minio_data.tar.gz",
    "layra_milvus_data.tar.gz",
    "layra_milvus_minio.tar.gz",
    "layra_milvus_etcd.tar.gz"
  ]
}
EOF
echo -e "${GREEN}✓ Metadata created${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    BACKUP COMPLETE                                          ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo "Backup saved to: $BACKUP_DIR"
echo "Total size: $(du -sh "$BACKUP_DIR" | cut -f1)"
echo ""
