#!/bin/bash
set -e

# 获取实例数量 (默认1)
INSTANCES=${UNOSERVER_INSTANCES:-1}

# 端口配置 (默认 XML-RPC:2003-2005, UNO:3003-2005)
BASE_PORT=${BASE_PORT:-2003}
BASE_UNO_PORT=${BASE_UNO_PORT:-3003}

echo "Starting $INSTANCES unoserver instances..."

# 顺序启动实例（避免资源竞争）
for i in $(seq 0 $(($INSTANCES - 1))); do
    PORT=$(($BASE_PORT + $i))
    UNO_PORT=$(($BASE_UNO_PORT + $i))
    
    echo "Starting instance $i on port $PORT (uno_port $UNO_PORT)"
    
    # 启动并等待就绪
    python3 -m unoserver.server \
        --port=$PORT \
        --uno-port=$UNO_PORT \
        --interface=0.0.0.0 \
        --uno-interface=0.0.0.0 \
        --conversion-timeout=300 &
    
    # 增加实例启动间隔
    sleep 3
    
    # 等待实例就绪
    echo "Waiting for instance $i to start..."
    while ! nc -z 0.0.0.0 $PORT; do
        sleep 1
        echo -n "."
    done
    echo " OK"
done

# 健康检查验证
sleep 2
for i in $(seq 0 $(($INSTANCES - 1))); do
    PORT=$(($BASE_PORT + $i))
    if ! nc -z 0.0.0.0 $PORT; then
        echo "ERROR: Unoserver instance on port $PORT failed to start"
        exit 1
    else
        echo "Unoserver on port $PORT is ready"
    fi
done

echo "All unoserver instances started successfully"
wait  # 保持容器运行直到所有子进程退出
