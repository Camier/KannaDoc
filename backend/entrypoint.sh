#!/bin/bash

set -e

wait_for_db() {
    # 更可靠的等待函数
    wait_for_service() {
        local host=$1
        local port=$2
        local max_retries=30
        local retry_interval=2
        local retry_count=0
        
        echo "等待服务 $host:$port 启动..."
        until (echo > /dev/tcp/"$host"/"$port") >/dev/null 2>&1 || [ $retry_count -eq $max_retries ]; do
            retry_count=$((retry_count+1))
            echo "尝试 $retry_count/$max_retries: 等待 $host:$port..."
            sleep $retry_interval
        done
        
        if [ $retry_count -eq $max_retries ]; then
            echo "错误: 服务 $host:$port 未能在 ${max_retries} 次重试后启动"
            exit 1
        fi
        
        echo "服务 $host:$port 已就绪"
    }

    # 等待所有依赖服务
    wait_for_service mysql 3306
    wait_for_service redis 6379
    wait_for_service mongodb 27017
    wait_for_service kafka 9092
    wait_for_service minio 9000

    # Wait for Milvus only if VECTOR_DB=milvus
    if [ "${VECTOR_DB:-milvus}" = "milvus" ]; then
        wait_for_service milvus-standalone 19530
    else
        echo "跳过 Milvus 等待 (VECTOR_DB=${VECTOR_DB:-milvus})"
    fi

    wait_for_service unoserver 2003

    # 设置日志环境变量
    export LOG_FILE=${LOG_FILE:-/proc/1/fd/1}  # 重定向到容器主进程的stdout

}

# 检查是否需要初始化迁移
check_migration_needed() {
    # 检查migrations目录是否存在
    if [ ! -f "migrations_previous/env.py" ]; then
        echo "初始化Alembic迁移环境..."
        # Remove existing migrations directory if it exists (from source code)
        rm -rf migrations
        alembic init migrations
        cp env.py migrations
        return 0
    else
        # Restore the snapshot contents without nesting migrations_previous into migrations/.
        #
        # Historically this used `cp -r migrations_previous/ migrations/`, which creates:
        # - migrations/migrations_previous/...
        # and then later backup logic copies migrations/* back into migrations_previous/,
        # causing an infinite-looking recursion:
        # - migrations_previous/migrations_previous/migrations_previous/...
        #
        # This shows up as a repo hygiene/drift issue when host paths are mounted.
        mkdir -p migrations
        shopt -s dotglob nullglob
        for item in migrations_previous/*; do
            cp -r "$item" migrations/
        done
        shopt -u dotglob nullglob
    fi
    
    # 检查数据库是否已应用最新迁移
    if ! alembic current | grep -q "head"; then
        return 0
    fi
    
    return 1
}

main() {
    wait_for_db

    if check_migration_needed; then
        echo "执行数据库迁移..."

        # Check if database has stale alembic_version entry (version exists in DB but not in migrations)
        if alembic current 2>&1 | grep -q "Can't locate revision"; then
            echo "检测到过时的数据库迁移版本，清理中..."
            # Drop the stale alembic_version table
            python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def clean_stale_migration():
    engine = create_async_engine('${DB_URL}')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if alembic_version table exists
        result = await session.execute(text(\"SHOW TABLES LIKE 'alembic_version'\"))
        if result.fetchone():
            await session.execute(text('DROP TABLE IF EXISTS alembic_version'))
            await session.commit()
            print('已清理过时的迁移版本')

    await engine.dispose()

asyncio.run(clean_stale_migration())
"
        fi

        set +e
        alembic revision --autogenerate -m "Init Mysql"
        REV_STATUS=$?
        set -e

        if [ $REV_STATUS -ne 0 ]; then
            echo "自动生成迁移失败，创建空的初始迁移以继续启动..."
        fi

        if ! ls migrations/versions/*.py >/dev/null 2>&1; then
            alembic revision -m "Init Mysql" --empty
        fi

        HAS_USERS_TABLE=$(python - <<'PY'
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def main() -> None:
    engine = create_async_engine(os.environ["DB_URL"])
    async with engine.connect() as conn:
        result = await conn.execute(text("SHOW TABLES LIKE 'users'"))
        print("1" if result.fetchone() else "0")
    await engine.dispose()

asyncio.run(main())
PY
)

        if [ "$HAS_USERS_TABLE" = "1" ]; then
            echo "检测到现有表，使用 stamp head 跳过建表"
            alembic stamp head
        else
            alembic upgrade head
        fi
        mkdir -p migrations_previous
        # Keep migrations_previous as a snapshot of migrations/ without ever copying a nested
        # migrations_previous directory back into itself.
        rm -rf migrations_previous/migrations_previous 2>/dev/null || true
        shopt -s dotglob nullglob
        for item in migrations/*; do
            base="$(basename "$item")"
            if [ "$base" = "migrations_previous" ]; then
                continue
            fi
            cp -r "$item" migrations_previous/
        done
        shopt -u dotglob nullglob
    else
        echo "数据库已是最新，无需迁移"
    fi

    exec gunicorn -c gunicorn_config.py app.main:app
}

main
