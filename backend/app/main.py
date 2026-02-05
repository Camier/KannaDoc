import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings, validate_settings
from app.core.logging import logger
from app.framework.app_framework import FastAPIFramework

from app.db.mysql_session import close_mysql
from app.db.mongo import mongodb
from app.db.redis import redis
from app.db.miniodb import async_minio_manager
from app.utils.kafka_producer import kafka_producer_manager
from app.utils.kafka_consumer import kafka_consumer_manager
from app.utils.prometheus_metrics import PrometheusMiddleware

framework = FastAPIFramework(debug_mode=settings.debug_mode)
app = framework.get_app()

# Instrument with Prometheus
app.middleware("http")(PrometheusMiddleware())

# Parse ALLOWED_ORIGINS from environment (comma-separated)
# Example: "http://localhost:3000,https://example.com"
allowed_origins_str = getattr(settings, "allowed_origins", "")
if allowed_origins_str:
    origins = [
        origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()
    ]
else:
    if settings.debug_mode:
        origins = ["*"]
    else:
        # Default for local production deployment
        origins = ["http://localhost:8090"]

# Enforcement of security best practices
if not settings.debug_mode:
    if not allowed_origins_str:
        raise RuntimeError(
            "SECURITY ERROR: ALLOWED_ORIGINS must be explicitly configured in non-debug mode. "
            "For local deployment, set ALLOWED_ORIGINS=http://localhost:8090 in your .env file."
        )
    if "*" in origins:
        raise RuntimeError(
            "SECURITY ERROR: Wildcard CORS origin ('*') is not allowed in non-debug mode. "
            "Please specify explicit origins in ALLOWED_ORIGINS."
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True
    if origins != ["*"]
    else False,  # Only allow credentials with specific origins
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()
    logger.info("FastAPI Started")
    await mongodb.connect()
    await kafka_producer_manager.start()
    await async_minio_manager.init_minio()
    consumer_task = asyncio.create_task(kafka_consumer_manager.consume_messages())

    async def shutdown_hook():
        logger.info("Stopping Kafka consumer...")
        await kafka_consumer_manager.stop()
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            logger.debug("Kafka consumer task cancelled during shutdown")

    app.state.shutdown_hook = shutdown_hook

    yield
    logger.info("Shutting down application services...")
    await shutdown_hook()
    await kafka_producer_manager.stop()
    await close_mysql()
    await mongodb.close()
    await redis.close()
    logger.info("FastAPI Closed")


app.router.lifespan_context = lifespan
framework.include_router(api_router)

_SAFE_SETTINGS_KEYS = (
    "api_version_url",
    "max_workers",
    "log_level",
    "log_file",
    "debug_mode",
    "server_ip",
    "kafka_broker_url",
    "kafka_topic",
    "kafka_partitions_number",
    "kafka_group_id",
    "minio_bucket_name",
    "embedding_model",
    "embedding_image_dpi",
    "unoserver_instances",
    "unoserver_host",
    "unoserver_base_port",
)

safe_settings = {k: getattr(settings, k, None) for k in _SAFE_SETTINGS_KEYS}
logger.info("FastAPI app started (safe settings): %s", safe_settings)
