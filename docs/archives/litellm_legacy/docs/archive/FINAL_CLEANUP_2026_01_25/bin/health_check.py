#!/usr/bin/env python3
"""
Health check for LiteLLM proxy ecosystem.
"""

import os
import sys
import time
import requests
import redis


def check_redis():
    """Check Redis connection."""
    try:
        host = os.environ.get("REDIS_HOST", "127.0.0.1")
        port = int(os.environ.get("REDIS_PORT", "6379"))
        password = os.environ.get("REDIS_PASSWORD") or None

        r = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=0,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

        if r.ping():
            info = r.info()
            return {
                "status": "healthy",
                "details": {
                    "version": info.get("redis_version", "unknown"),
                    "memory_used": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                },
            }
        else:
            return {"status": "unhealthy", "error": "Redis ping failed"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_litellm_proxy():
    """Check LiteLLM proxy health."""
    base_url = os.environ.get("LITELLM_BASE", "http://127.0.0.1:4000")

    base = base_url.rstrip("/")
    key = (
        os.environ.get("LITELLM_HEALTH_API_KEY")
        or os.environ.get("LITELLM_API_KEY")
        or os.environ.get("LITELLM_MASTER_KEY")
    )
    headers = {"Authorization": f"Bearer {key}"} if key else None

    try:
        # Liveness should always be public.
        health = requests.get(f"{base}/health/liveliness", timeout=2)
        if health.status_code != 200:
            return {"status": "unhealthy", "error": f"/health/liveliness -> {health.status_code}"}

        # Readiness can be 503 when dependencies (e.g. Redis) are down.
        ready = requests.get(f"{base}/health/readiness", timeout=3)

        # /v1/models requires auth when the proxy is configured with a master key.
        # Treat 401 as "reachable but auth required" if no key is provided.
        models = requests.get(f"{base}/v1/models", headers=headers, timeout=5)
        models_ok = models.status_code in (200, 401)

        status = "healthy"
        if ready.status_code != 200:
            status = "degraded"
        if not models_ok:
            status = "unhealthy"

        return {
            "status": status,
            "details": {
                "healthz": health.status_code,
                "readyz": ready.status_code,
                "models": models.status_code,
            },
        }
    except requests.RequestException as e:
        return {"status": "unhealthy", "error": str(e)}



def main():
    """Run all health checks."""
    print("=" * 60)
    print("LITELLM PROXY HEALTH CHECK")
    print("=" * 60)
    print(f"Time: {time.ctime()}")
    print()

    checks = [
        ("Redis", check_redis),
        ("LiteLLM Proxy", check_litellm_proxy),
    ]

    healthy_count = 0
    total_checks = len(checks)

    for name, check_func in checks:
        start = time.time()
        result = check_func()
        latency = time.time() - start

        status = result.get("status", "unknown")
        status_symbol = "✅" if status == "healthy" else ("⚠️" if status == "degraded" else "❌")

        print(f"{status_symbol} {name:<20} {status:<10} {latency:.3f}s")

        if status == "healthy":
            healthy_count += 1
            # Print all result keys except 'status'
            for key, value in result.items():
                if key != "status" and key != "latency":
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            print(f"    {subkey}: {subvalue}")
                    else:
                        print(f"    {key}: {value}")
        else:
            error = result.get("error", "Unknown error")
            print(f"    Error: {error}")

    print()
    print("=" * 60)
    print(f"SUMMARY: {healthy_count}/{total_checks} services healthy")

    if healthy_count == total_checks:
        print("✅ All systems operational")
        return 0
    elif healthy_count == 0:
        print("❌ All systems down")
        return 1
    else:
        print("⚠️  System degraded")
        return 2


if __name__ == "__main__":
    sys.exit(main())
