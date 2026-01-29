#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    DATABASE ROLLBACK SCRIPT                                    ║
# ║                    Restore databases from backups                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Usage: ./deploy/rollback/db_rollback.sh <database> <backup-file>
#
# Examples:
#   ./deploy/rollback/db_rollback.sh mysql /tmp/mysql_backup_20260127.sql
#   ./deploy/rollback/db_rollback.sh mongodb /tmp/mongo_dump
#   ./deploy/rollback/db_rollback.sh redis /tmp/redis_dump.rdb
#
# WARNING: This will DATA LOSS since the backup was created

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

DATABASE="${1:-}"
BACKUP_FILE="${2:-}"

# Available databases
DATABASES=("mysql" "mongodb" "redis" "milvus" "qdrant")

if [ -z "$DATABASE" ]; then
    echo -e "${RED}Error: Database name required${NC}"
    echo ""
    echo "Usage: $0 <database> <backup-file>"
    echo ""
    echo "Available databases:"
    printf '  - %s\n' "${DATABASES[@]}"
    exit 1
fi

if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file path required${NC}"
    echo ""
    echo "Usage: $0 <database> <backup-file>"
    echo ""
    echo "Recent backups:"
    ls -lt /tmp/*mysql*.sql /tmp/*mongo*.rdb /tmp/*redis*.rdb 2>/dev/null | head -10
    exit 1
fi

# Validate backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Load environment
if [ -f .env ]; then
    source .env
else
    echo -e "${RED}✗ .env file not found${NC}"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    DATABASE ROLLBACK: $DATABASE                            ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Backup file: $BACKUP_FILE${NC}"
echo -e "${YELLOW}Backup size: $(du -h "$BACKUP_FILE" | cut -f1)${NC}"
echo -e "${YELLOW}Backup date: $(stat -c %y "$BACKUP_FILE")${NC}"
echo ""

# Multiple confirmations for safety
echo -e "${RED}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║ WARNING: THIS WILL CAUSE DATA LOSS                                        ║${NC}"
echo -e "${RED}║ All data since this backup will be PERMANENTLY DELETED                    ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Type 'I UNDERSTAND' to continue:"
read confirmation
if [ "$confirmation" != "I UNDERSTAND" ]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/3] Creating pre-rollback backup...${NC}"

# Create backup of current state before restoring
PRE_BACKUP_DIR="/tmp/layra_before_db_restore_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$PRE_BACKUP_DIR"

case "$DATABASE" in
    mysql)
        docker exec layra-mysql mysqldump -u root -p"${MYSQL_ROOT_PASSWORD:-root}" \
            --all-databases --single-transaction \
            > "$PRE_BACKUP_DIR/mysql_pre_restore.sql"
        echo -e "${GREEN}✓ Pre-rollback MySQL backup saved${NC}"
        ;;
    mongodb)
        docker exec layra-mongodb mongodump \
            --username "${MONGODB_ROOT_USERNAME}" \
            --password "${MONGODB_ROOT_PASSWORD}" \
            --authenticationDatabase admin \
            --out /tmp/mongo_pre_restore
        docker cp layra-mongodb:/tmp/mongo_pre_restore "$PRE_BACKUP_DIR/mongo_pre_restore"
        echo -e "${GREEN}✓ Pre-rollback MongoDB backup saved${NC}"
        ;;
    redis)
        docker exec layra-redis redis-cli -a "${REDIS_PASSWORD}" save
        docker cp layra-redis:/data/dump.rdb "$PRE_BACKUP_DIR/redis_pre_restore.rdb"
        echo -e "${GREEN}✓ Pre-rollback Redis backup saved${NC}"
        ;;
esac

echo -e "${YELLOW}[2/3] Stopping dependent services...${NC}"

# Stop services that depend on the database
docker compose stop backend
echo -e "${GREEN}✓ Backend stopped${NC}"

echo -e "${YELLOW}[3/3] Restoring database...${NC}"

case "$DATABASE" in
    mysql)
        echo "Restoring MySQL from $BACKUP_FILE..."
        docker exec -i layra-mysql mysql -u root -p"${MYSQL_ROOT_PASSWORD:-root}" < "$BACKUP_FILE"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ MySQL restored successfully${NC}"
        else
            echo -e "${RED}✗ MySQL restore failed${NC}"
            echo "Pre-restore backup saved at: $PRE_BACKUP_DIR"
            exit 1
        fi
        ;;

    mongodb)
        echo "Restoring MongoDB from $BACKUP_FILE..."
        # Check if backup is a directory or archive
        if [ -d "$BACKUP_FILE" ]; then
            docker cp "$BACKUP_FILE" layra-mongodb:/tmp/mongo_restore
            docker exec layra-mongodb mongorestore \
                --username "${MONGODB_ROOT_USERNAME}" \
                --password "${MONGODB_ROOT_PASSWORD}" \
                --authenticationDatabase admin \
                --drop \
                /tmp/mongo_restore
        else
            echo -e "${RED}✗ MongoDB backup must be a directory from mongodump${NC}"
            exit 1
        fi
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ MongoDB restored successfully${NC}"
        else
            echo -e "${RED}✗ MongoDB restore failed${NC}"
            echo "Pre-restore backup saved at: $PRE_BACKUP_DIR"
            exit 1
        fi
        ;;

    redis)
        echo "Restoring Redis from $BACKUP_FILE..."
        # Stop Redis, copy file, start Redis
        docker compose stop redis
        docker cp "$BACKUP_FILE" layra-redis:/data/dump.rdb
        docker compose start redis
        sleep 5
        if docker ps | grep -q "layra-redis.*Up"; then
            echo -e "${GREEN}✓ Redis restored successfully${NC}"
        else
            echo -e "${RED}✗ Redis failed to start after restore${NC}"
            echo "Pre-restore backup saved at: $PRE_BACKUP_DIR"
            exit 1
        fi
        ;;

    milvus)
        echo "Restoring Milvus data volume..."
        # Stop Milvus services
        docker compose stop milvus-standalone milvus-etcd milvus-minio

        # Extract backup to volume
        docker run --rm \
            -v layra_milvus_data:/data \
            -v "$(dirname "$BACKUP_FILE"):/backup" \
            alpine sh -c "rm -rf /data/* && tar xzf /backup/$(basename "$BACKUP_FILE") -C /data"

        # Start services
        docker compose start milvus-etcd milvus-minio milvus-standalone
        echo -e "${GREEN}✓ Milvus data restored${NC}"
        ;;

    qdrant)
        echo "Restoring Qdrant data volume..."
        docker compose stop qdrant

        docker run --rm \
            -v layra_qdrant_data:/data \
            -v "$(dirname "$BACKUP_FILE"):/backup" \
            alpine sh -c "rm -rf /data/* && tar xzf /backup/$(basename "$BACKUP_FILE") -C /data"

        docker compose start qdrant
        echo -e "${GREEN}✓ Qdrant data restored${NC}"
        ;;

    *)
        echo -e "${RED}✗ Unknown database: $DATABASE${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${YELLOW}Restarting dependent services...${NC}"
docker compose start backend
sleep 10

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    DATABASE ROLLBACK COMPLETE                                ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓ Database $DATABASE restored successfully${NC}"
echo ""
echo -e "${YELLOW}Pre-restore backup saved at: $PRE_BACKUP_DIR${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify data integrity"
echo "  2. Restart application services"
echo "  3. Run verification: ./deploy/rollback/verify_rollback.sh"
echo "  4. Monitor logs: docker compose logs -f backend"
echo ""
echo -e "${YELLOW}To revert this restore:${NC}"
echo "  $0 $DATABASE $PRE_BACKUP_DIR/*"
echo ""
