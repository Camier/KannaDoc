FROM debian:bookworm-slim

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 阿里云镜像源
RUN echo "deb http://mirrors.aliyun.com/debian bookworm main non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian bookworm-updates main non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian bookworm-backports main non-free non-free-firmware" >> /etc/apt/sources.list

# 删除其他可能的源文件
RUN rm -rf /etc/apt/sources.list.d/*

# 安装 LibreOffice 和依赖
RUN apt-get update -o Acquire::Check-Valid-Until=false -o Acquire::AllowInsecureRepositories=true && \
    apt-get install -y --allow-unauthenticated \
        libreoffice \
        python3-pip \
        netcat-openbsd \
        ttf-wqy-zenhei \
        ttf-wqy-microhei \
        fonts-noto-cjk \
        fonts-noto-cjk-extra \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境并安装unoserver
RUN python3 -m pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple unoserver --break-system-packages

# 添加启动脚本
COPY start_unoservers.sh /app/
RUN chmod +x /app/start_unoservers.sh

WORKDIR /app
CMD ["/app/start_unoservers.sh"]