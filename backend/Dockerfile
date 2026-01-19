FROM python:3.10-slim-bookworm

# Set timezone (Optional: can be removed if not strictly needed, keeping for compatibility)
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        poppler-utils \
        git \
        curl \
        docker.io \
        netcat-openbsd \
        locales \
        ttf-wqy-zenhei \
        ttf-wqy-microhei \
        fonts-noto-cjk \
        fonts-noto-cjk-extra \
    && rm -rf /var/lib/apt/lists/* && \
    localedef -i zh_CN -c -f UTF-8 -A /usr/share/locale/locale.alias zh_CN.UTF-8

# Set locale
ENV LANG zh_CN.utf8

# Create docker group (commented out as in original)
# RUN groupadd docker && usermod -aG docker root

WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies from official PyPI
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Clean Python cache to avoid stale bytecode
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Set entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create sandbox shared directory
RUN mkdir -p /app/sandbox_workspace && chmod 777 /app/sandbox_workspace

ENTRYPOINT ["/entrypoint.sh"]