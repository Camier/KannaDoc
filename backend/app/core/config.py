"""Application settings and environment configuration."""

import importlib
import logging

_pydantic = importlib.import_module("pydantic")
_pydantic_settings = importlib.import_module("pydantic_settings")

Field = _pydantic.Field
BaseSettings = _pydantic_settings.BaseSettings

logger = logging.getLogger(__name__)


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
    redis_task_db: int = 1
    redis_lock_db: int = 2
    mongodb_url: str = "localhost:27017"
    mongodb_db: str = "chat_mongodb"
    # SECURITY: Removed hardcoded credentials - must be set via environment variables
    mongodb_root_username: str = ""
    mongodb_root_password: str = ""
    mongodb_pool_size: int = 50
    mongodb_min_pool_size: int = 10
    debug_mode: bool = False

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
    hnsw_m: int = Field(
        default=48, ge=4, le=64, description="HNSW M parameter for Milvus index"
    )
    hnsw_ef_construction: int = Field(
        default=1024, ge=8, description="HNSW efConstruction for Milvus index"
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
    single_tenant_mode: bool = True
    default_username: str = "miko"
    allowed_origins: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins (e.g., 'http://localhost:3000,https://example.com'). Empty = allow all (development only)",
    )

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

    # Retrieval modes
    # - dense: dense-only candidate generation + exact MaxSim rerank on patch vectors (ColPali-style)
    # - hybrid: Milvus hybrid search (dense + sparse) on collections that have both fields
    # - sparse_then_rerank: sparse page recall -> exact MaxSim rerank on patch vectors
    # - dual_then_rerank: sparse page recall + dense patch recall -> fuse -> exact MaxSim rerank
    rag_retrieval_mode: str = Field(
        default="dense",
        description="RAG retrieval mode: dense|hybrid|sparse_then_rerank|dual_then_rerank",
    )
    rag_pages_sparse_suffix: str = Field(
        default="_pages_sparse",
        description="Suffix for the page-level sparse collection derived from a patch collection name.",
    )

    # top_K defaults/caps are intentionally higher than the legacy UI defaults in thesis env.
    rag_default_top_k: int = Field(
        default=50, ge=1, le=500, description="Default top_K when model_config sets -1."
    )
    rag_top_k_cap: int = Field(
        default=120,
        ge=1,
        le=500,
        description="Hard cap for top_K to prevent runaway retrieval.",
    )

    # Diversification: ensure broad queries return multiple distinct documents.
    rag_diverse_file_limit: int = Field(
        default=20,
        ge=1,
        le=200,
        description="Target number of distinct file_id in candidate set.",
    )
    rag_diverse_pages_per_file_cap: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max number of pages per file_id to keep when diversifying candidates.",
    )

    # When Mongo metadata is missing, we fallback to local previews; keep this bounded for prompt size.
    rag_fallback_text_cap: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Max number of fallback page previews injected.",
    )

    # Hybrid Search Configuration
    rag_hybrid_enabled: bool = False
    rag_hybrid_ranker: str = (
        "rrf"  # "rrf" | "weighted" - RRF is default (score-invariant)
    )
    rag_hybrid_rrf_k: int = (
        60  # RRF smoothing constant (default: 60, lower = emphasize top ranks)
    )
    rag_hybrid_dense_weight: float = 0.7  # Only used if ranker="weighted"
    rag_hybrid_sparse_weight: float = 0.3  # Only used if ranker="weighted"

    model_config = {"extra": "ignore", "env_file": "../.env"}


def validate_settings() -> None:
    """Validate that required security settings are configured.

    Raises:
        ValueError: If critical security settings are missing or empty
    """
    critical_settings = {
        "db_url": settings.db_url,
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

    if settings.rag_hybrid_enabled:
        if not (0.0 <= settings.rag_hybrid_dense_weight <= 1.0):
            raise ValueError(
                f"rag_hybrid_dense_weight must be between 0.0 and 1.0, got {settings.rag_hybrid_dense_weight}"
            )
        if not (0.0 <= settings.rag_hybrid_sparse_weight <= 1.0):
            raise ValueError(
                f"rag_hybrid_sparse_weight must be between 0.0 and 1.0, got {settings.rag_hybrid_sparse_weight}"
            )
        if settings.rag_hybrid_ranker not in ["rrf", "weighted"]:
            raise ValueError(
                f"rag_hybrid_ranker must be 'rrf' or 'weighted', got {settings.rag_hybrid_ranker}"
            )
        if settings.rag_hybrid_rrf_k <= 0:
            raise ValueError(
                f"rag_hybrid_rrf_k must be a positive integer, got {settings.rag_hybrid_rrf_k}"
            )

        if not (10 <= settings.rag_hybrid_rrf_k <= 100):
            logger.warning(
                f"Unusual rag_hybrid_rrf_k value: {settings.rag_hybrid_rrf_k}. Recommended range is [10, 100]."
            )

        if (
            abs(
                (settings.rag_hybrid_dense_weight + settings.rag_hybrid_sparse_weight)
                - 1.0
            )
            > 1e-6
        ):
            logger.warning(
                f"Hybrid weights (dense={settings.rag_hybrid_dense_weight}, sparse={settings.rag_hybrid_sparse_weight}) "
                f"sum to {settings.rag_hybrid_dense_weight + settings.rag_hybrid_sparse_weight}, not 1.0."
            )

        logger.info(
            f"Hybrid search: ranker={settings.rag_hybrid_ranker}, rrf_k={settings.rag_hybrid_rrf_k}"
        )

    if settings.rag_retrieval_mode not in [
        "dense",
        "hybrid",
        "sparse_then_rerank",
        "dual_then_rerank",
    ]:
        raise ValueError(
            "rag_retrieval_mode must be one of: dense, hybrid, sparse_then_rerank, dual_then_rerank. "
            f"Got: {settings.rag_retrieval_mode}"
        )


settings = Settings()
