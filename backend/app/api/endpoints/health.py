import asyncio
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.logging import logger
from app.utils.prometheus_metrics import get_metrics

router = APIRouter()

# Timeout for each dependency check (seconds)
HEALTH_CHECK_TIMEOUT = 2.0


async def _check_mysql() -> dict[str, Any]:
    """Check MySQL connectivity via async engine."""
    try:
        from app.db.mysql_session import mysql

        async with mysql.async_session() as session:
            await asyncio.wait_for(
                session.execute(text("SELECT 1")),
                timeout=HEALTH_CHECK_TIMEOUT,
            )
        return {"status": "healthy", "latency_ms": None}
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "error": "timeout"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_mongodb() -> dict[str, Any]:
    """Check MongoDB connectivity via motor client."""
    try:
        from app.db.mongo import mongodb

        if mongodb.client is None:
            return {"status": "unhealthy", "error": "client not initialized"}
        await asyncio.wait_for(
            mongodb.client.admin.command("ping"),
            timeout=HEALTH_CHECK_TIMEOUT,
        )
        return {"status": "healthy", "latency_ms": None}
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "error": "timeout"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_redis() -> dict[str, Any]:
    """Check Redis connectivity via async redis."""
    try:
        from app.db.redis import redis

        conn = await redis.get_redis_connection(db=0)
        await asyncio.wait_for(
            conn.ping(),
            timeout=HEALTH_CHECK_TIMEOUT,
        )
        return {"status": "healthy", "latency_ms": None}
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "error": "timeout"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_milvus() -> dict[str, Any]:
    """Check Milvus connectivity via MilvusManager."""
    try:
        from app.db.milvus import milvus_client

        # Run synchronous health_check in executor to avoid blocking
        loop = asyncio.get_event_loop()
        is_healthy = await asyncio.wait_for(
            loop.run_in_executor(None, milvus_client.health_check),
            timeout=HEALTH_CHECK_TIMEOUT,
        )
        if is_healthy:
            return {"status": "healthy", "latency_ms": None}
        return {"status": "unhealthy", "error": "health_check returned False"}
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "error": "timeout"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_minio() -> dict[str, Any]:
    """Check MinIO connectivity via aioboto3."""
    try:
        from app.db.miniodb import async_minio_manager

        async with async_minio_manager.session.client(
            "s3",
            endpoint_url=async_minio_manager.minio_url,
            aws_access_key_id=async_minio_manager.access_key,
            aws_secret_access_key=async_minio_manager.secret_key,
            use_ssl=False,
        ) as client:
            await asyncio.wait_for(
                client.list_buckets(),
                timeout=HEALTH_CHECK_TIMEOUT,
            )
        return {"status": "healthy", "latency_ms": None}
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "error": "timeout"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_kafka() -> dict[str, Any]:
    """Check Kafka connectivity via aiokafka producer."""
    try:
        from aiokafka import AIOKafkaProducer

        from app.core.config import settings

        producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_broker_url,
            request_timeout_ms=int(HEALTH_CHECK_TIMEOUT * 1000),
        )
        try:
            await asyncio.wait_for(
                producer.start(),
                timeout=HEALTH_CHECK_TIMEOUT,
            )
            return {"status": "healthy", "latency_ms": None}
        finally:
            await producer.stop()
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "error": "timeout"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


# Liveness probe - simple, fast, always returns UP
@router.get("/check", response_model=dict)
async def health_check():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "UP", "details": "All systems operational"},
    )


# Readiness probe - deep checks for all dependencies
@router.get("/ready", response_model=dict)
async def readiness_check():
    """
    Deep health check that verifies all dependencies are accessible.
    Returns structured JSON with individual service status.

    Used as Kubernetes readiness probe - only return 200 if all critical
    dependencies are healthy.
    """
    checks = {}

    # Run all checks concurrently for faster response
    results = await asyncio.gather(
        _check_mysql(),
        _check_mongodb(),
        _check_redis(),
        _check_milvus(),
        _check_minio(),
        _check_kafka(),
        return_exceptions=True,
    )

    service_names = ["mysql", "mongodb", "redis", "milvus", "minio", "kafka"]

    for name, result in zip(service_names, results):
        if isinstance(result, Exception):
            checks[name] = {"status": "unhealthy", "error": str(result)[:100]}
        else:
            checks[name] = result

    # Determine overall status
    unhealthy_count = sum(1 for c in checks.values() if c["status"] == "unhealthy")
    if unhealthy_count == 0:
        overall_status = "healthy"
        http_status = status.HTTP_200_OK
    elif unhealthy_count < len(checks):
        overall_status = "degraded"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        overall_status = "unhealthy"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    logger.info(
        f"Readiness check: {overall_status} ({unhealthy_count}/{len(checks)} unhealthy)"
    )

    return JSONResponse(
        status_code=http_status,
        content={
            "status": overall_status,
            "checks": checks,
        },
    )


@router.get("/metrics")
async def metrics():
    return get_metrics()
