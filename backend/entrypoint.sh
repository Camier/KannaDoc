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
        until (echo > /dev/tcp/$host/$port) >/dev/null 2>&1 || [ $retry_count -eq $max_retries ]; do
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
    wait_for_service milvus-standalone 19530

    # 设置日志环境变量
    export LOG_FILE=${LOG_FILE:-/proc/1/fd/1}  # 重定向到容器主进程的stdout

}

# 检查是否需要初始化迁移
check_migration_needed() {
    # 检查migrations目录是否存在
    if [ ! -f "migrations_previous/env.py" ]; then
        echo "初始化Alembic迁移环境..."
        alembic init migrations
        cp env.py migrations
        return 0
    else
        cp -r migrations_previous/ migrations/
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
        alembic revision --autogenerate -m "Init Mysql"
        alembic upgrade head
        cp -r migrations/* migrations_previous/
    else
        echo "数据库已是最新，无需迁移"
    fi
    
    exec gunicorn -c gunicorn_config.py app.main:app
}

main