FROM alpine:latest

RUN apk add --no-cache git git-lfs jq

WORKDIR /model_weights

# 复制脚本到容器内 - 确保文件名完全匹配
COPY init_models.sh /init_models.sh
RUN chmod +x /init_models.sh

# 设置环境变量默认值
# ENV MODEL_BASE_URL=https://hf-mirror.com/vidore

ENTRYPOINT ["/init_models.sh"]