from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_version_url: str = "/api/v1"
    max_workers: int = 10
    log_level: str = "INFO"
    log_file: str = "app.log"
    db_url: str = "mysql+asyncmy://username:password@localhost/dbname"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    redis_url: str = "localhost:6379"
    redis_password: str = "redispassword"
    redis_token_db: int = 0
    redis_task_db: int = 1
    redis_lock_db: int = 2
    secret_key: str = "your_secret_key_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 8
    mongodb_url: str = "localhost:27017"
    mongodb_db: str = "chat_mongodb"
    mongodb_root_username: str = "testuser"
    mongodb_root_password: str = "testpassword"
    mongodb_pool_size: int = 100
    mongodb_min_pool_size: int = 10
    debug_mode: bool = False
    kafka_broker_url: str = "localhost:9094"
    kafka_topic: str = "task_generation"
    kafka_partitions_number: int = 10
    kafka_group_id: str = "task_consumer_group"
    minio_url: str = Field(
        default="http://localhost:9000", description="MinIO API endpoint"
    )
    minio_access_key: str = "your_access_key"
    minio_secret_key: str = "your_secret_key"
    minio_bucket_name: str = "minio-file"
    milvus_uri: str = Field(
        ..., description="Milvus connection URI, e.g., http://localhost:19530"
    )
    colbert_model_path: str = "/model_weights/colqwen2.5-v0.2"
    sandbox_shared_volume: str = "/app/sandbox_workspace"
    server_ip: str = "http://localhost"
    allowed_origins: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins (e.g., 'http://localhost:3000,https://example.com'). Empty = allow all (development only)"
    )
    unoserver_instances: int = 1
    unoserver_host: str = "unoserver"
    unoserver_base_port: int = 2003
    embedding_image_dpi: int = 200
    embedding_model: str = "local_colqwen"
    jina_api_key: str = ""
    jina_embeddings_v4_url: str = "https://api.jina.ai/v1/embeddings"

    # Simple Auth Settings (for solo/development use)
    simple_auth_mode: bool = Field(
        default=False,
        description="Enable simple API key auth (no registration, single user)",
    )
    simple_api_key: str = Field(
        default="layra-dev-key-2024", description="API key for simple auth mode"
    )
    simple_username: str = Field(
        default="layra", description="Username for simple auth mode"
    )
    simple_password: str = Field(
        default="layra123", description="Password for simple auth mode"
    )

    model_config = {"extra": "ignore", "env_file": "../.env"}


settings = Settings()
