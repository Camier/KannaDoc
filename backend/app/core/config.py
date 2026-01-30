"""Application settings and environment configuration."""

import importlib

_pydantic = importlib.import_module("pydantic")
_pydantic_settings = importlib.import_module("pydantic_settings")

Field = _pydantic.Field
BaseSettings = _pydantic_settings.BaseSettings


class Settings(BaseSettings):
    api_version_url: str = "/api/v1"
    max_workers: int = 10
    log_level: str = "INFO"
    log_file: str = "app.log"
    # SECURITY: Removed hardcoded credentials - must be set via environment variables
    db_url: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20
    redis_url: str = "localhost:6379"
    # SECURITY: Removed hardcoded password - must be set via environment variables
    redis_password: str = ""
    redis_token_db: int = 0
    redis_task_db: int = 1
    redis_lock_db: int = 2
    # SECURITY: Removed hardcoded secret key - must be set via environment variables
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 8
    mongodb_url: str = "localhost:27017"
    mongodb_db: str = "chat_mongodb"
    # SECURITY: Removed hardcoded credentials - must be set via environment variables
    mongodb_root_username: str = ""
    mongodb_root_password: str = ""
    mongodb_pool_size: int = 50
    mongodb_min_pool_size: int = 10
    debug_mode: bool = False
    # Authz / Tenancy
    # When enabled, username-based access checks are bypassed and all users share the same data.
    single_tenant_mode: bool = False

    # Infrastructure - Kafka
    kafka_broker_url: str = "localhost:9094"
    kafka_topic: str = "task_generation"
    kafka_partitions_number: int = 10
    kafka_group_id: str = "task_consumer_group"

    # Infrastructure - MinIO
    # minio_url is for INTERNAL backend-to-minio traffic (e.g., http://minio:9000 in Docker)
    minio_url: str = Field(
        default="http://minio:9000",
        description="MinIO internal API endpoint for backend services",
    )
    # minio_public_url is for EXTERNAL browser-to-minio traffic (e.g., http://your-ip:9000)
    # CRITICAL: For external downloads, must be set to actual server IP/domain
    # Falls back to server_ip + minio_public_port if not set (Docker/internal use only)
    # For production: Set MINIO_PUBLIC_URL environment variable to your public server address
    minio_public_url: str = Field(
        default="",  # Will use server_ip + minio_public_port as fallback
        description="MinIO public endpoint for user downloads (set MINIO_PUBLIC_URL env var for production)",
    )
    minio_public_port: int = Field(
        default=9000,
        description="MinIO public port (used if MINIO_PUBLIC_URL not set)",
    )
    # SECURITY: Removed hardcoded credentials - must be set via environment variables
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket_name: str = "minio-file"

    # Infrastructure - Vector DB
    milvus_uri: str = Field(
        ..., description="Milvus connection URI, e.g., http://localhost:19530"
    )
    vector_db: str = Field(
        default="milvus", description="Vector database backend: milvus"
    )

    # Models & Sandbox
    colbert_model_path: str = "/model_weights/colqwen2.5-v0.2"
    sandbox_shared_volume: str = "/app/sandbox_workspace"

    # Model Server Configuration
    model_server_url: str = Field(
        default="http://model-server:8005",
        description="Model server URL for embeddings and inference",
    )

    # Server & Networking
    # server_ip is the base URL for the application server
    server_ip: str = "http://localhost"
    allowed_origins: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins (e.g., 'http://localhost:3000,https://example.com'). Empty = allow all (development only)",
    )

    # Neo4j Configuration (for future scaling - Knowledge Graph integration)
    # Currently reserved for upcoming roadmap features.
    # neo4j_uri: str = "bolt://localhost:7687"
    # neo4j_user: str = "neo4j"
    # neo4j_password: str = "password"
    unoserver_instances: int = 1
    unoserver_host: str = "unoserver"
    unoserver_base_port: int = 2003
    embedding_image_dpi: int = 200
    embedding_model: str = "local_colqwen"
    jina_api_key: str = ""
    jina_embeddings_v4_url: str = "https://api.jina.ai/v1/embeddings"
    rag_max_query_vecs: int = 48
    rag_search_limit_cap: int = 120
    rag_candidate_images_cap: int = 120
    rag_search_limit_min: int = 50
    rag_ef_min: int = 100
    rag_load_collection_once: bool = True

    model_config = {"extra": "ignore", "env_file": "../.env"}


def validate_settings() -> None:
    """Validate that required security settings are configured.

    Raises:
        ValueError: If critical security settings are missing or empty
    """
    critical_settings = {
        "db_url": settings.db_url,
        "secret_key": settings.secret_key,
        "mongodb_root_username": settings.mongodb_root_username,
        "mongodb_root_password": settings.mongodb_root_password,
        "minio_access_key": settings.minio_access_key,
        "minio_secret_key": settings.minio_secret_key,
    }

    missing = [name for name, value in critical_settings.items() if not value]

    if missing:
        raise ValueError(
            f"SECURITY ERROR: Required settings not configured: {', '.join(missing)}. "
            "Please set these via environment variables before starting the server."
        )


settings = Settings()
