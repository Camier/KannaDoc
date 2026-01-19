FROM alpine:latest

# Install dependencies
RUN apk add --no-cache git git-lfs jq

WORKDIR /model_weights

# Copy script to container - ensure filename matches exactly
COPY init_models.sh /init_models.sh
RUN chmod +x /init_models.sh

# Set environment variable default
# ENV MODEL_BASE_URL=https://huggingface.co/vidore

ENTRYPOINT ["/init_models.sh"]