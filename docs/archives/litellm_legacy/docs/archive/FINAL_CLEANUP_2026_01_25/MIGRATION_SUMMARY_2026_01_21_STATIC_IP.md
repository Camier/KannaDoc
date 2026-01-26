# Docker Migration: Status Update (Static IP Workaround)

**Date:** 2026-01-21
**Status:** ✅ **SUCCESS (with Workaround)**

## The Issue
Docker internal DNS resolution was failing persistently on this host (`ConnectionRefused` and `Temporary failure in name resolution`), preventing the LiteLLM container from reaching the PostgreSQL and Redis containers by hostname.

## The Fix
We switched to a **Static IP configuration** for the Docker network to bypass DNS completely.

### Network Configuration
- **Subnet:** `172.20.0.0/16`
- **Gateway:** `172.20.0.1`

### Service IPs
- **PostgreSQL:** `172.20.0.5`
- **Redis:** `172.20.0.6`
- **LiteLLM Proxy:** `172.20.0.10`

### Image Used
- **Image:** `litellm/litellm:latest` (Docker Hub)
- **Reason:** The `ghcr.io` image (Wolfi-based) lacked debugging tools and had stricter network policies. The Docker Hub image (Debian-based) proved more stable in this environment.

## Verification
- **Liveness Check:** `curl http://localhost:4000/health/liveliness` -> `200 OK`
- **Database Connection:** Verified via logs (connected, detected schema changes).
- **Redis Connection:** Verified connectivity from container, config applied.

## Next Steps
- Monitor logs with `docker logs -f litellm-proxy`.
- If schema errors persist, run `docker exec litellm-proxy prisma migrate deploy`.
