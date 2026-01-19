#!/bin/bash
set -e

# Configuration
BACKUP_ROOT="/mnt/btrfs_LAB/snapshots/layra"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAPSHOT_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
CONTAINER_MYSQL="layra-mysql"
CONTAINER_MONGO="layra-mongodb"
CONTAINER_REDIS="layra-redis"

# Ensure backup directory exists
mkdir -p "${SNAPSHOT_DIR}"

echo "📸 Starting LAYRA Data Snapshot: ${TIMESTAMP}"
echo "📂 Destination: ${SNAPSHOT_DIR}"

# 1. MySQL Dump
echo "--------------------------------"
echo "📦 Backing up MySQL (Metadata)..."
docker exec "${CONTAINER_MYSQL}" mysqldump -u root -pdb_root_sec_1a2b3c --all-databases > "${SNAPSHOT_DIR}/mysql_dump.sql"
if [ $? -eq 0 ]; then echo "✅ MySQL backup success"; else echo "❌ MySQL backup failed"; fi

# 2. MongoDB Dump
echo "--------------------------------"
echo "📦 Backing up MongoDB (Chat History)..."
docker exec "${CONTAINER_MONGO}" mongodump --username layra --password mongo_sec_7g8h9i --authenticationDatabase admin --out /tmp/mongo_dump
docker cp "${CONTAINER_MONGO}:/tmp/mongo_dump" "${SNAPSHOT_DIR}/mongo_dump"
docker exec "${CONTAINER_MONGO}" rm -rf /tmp/mongo_dump
if [ $? -eq 0 ]; then echo "✅ MongoDB backup success"; else echo "❌ MongoDB backup failed"; fi

# 3. Redis Dump
echo "--------------------------------"
echo "📦 Backing up Redis (Cache/Queue)..."
docker exec "${CONTAINER_REDIS}" redis-cli -a redis_sec_0j1k2l save
docker cp "${CONTAINER_REDIS}:/data/dump.rdb" "${SNAPSHOT_DIR}/redis_dump.rdb"
if [ $? -eq 0 ]; then echo "✅ Redis backup success"; else echo "❌ Redis backup failed"; fi

# 4. Volume Backups (MinIO & Milvus)
# Note: This uses a temporary alpine container to mount the volumes and tar them.
# This is safer than direct file copying and works for named volumes.
echo "--------------------------------"
echo "📦 Backing up MinIO & Milvus Volumes (Knowledge Base)..."

# Define volumes to backup
VOLUMES=("layra_minio_data" "layra_milvus_data" "layra_milvus_etcd" "layra_milvus_minio")

for VOL in "${VOLUMES[@]}"; do
    echo "   - Archiving volume: ${VOL}..."
    docker run --rm \
        -v "${VOL}:/volume_data" \
        -v "${SNAPSHOT_DIR}:/backup" \
        alpine tar czf "/backup/${VOL}.tar.gz" -C /volume_data .
done
echo "✅ Volume archives created"

# 5. Metadata
echo "--------------------------------"
echo "📝 Saving Metadata..."
echo "Timestamp: ${TIMESTAMP}" > "${SNAPSHOT_DIR}/info.txt"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" >> "${SNAPSHOT_DIR}/info.txt"

echo "--------------------------------"
echo "🎉 Snapshot Complete!"
echo "👉 Path: ${SNAPSHOT_DIR}"
du -sh "${SNAPSHOT_DIR}"
