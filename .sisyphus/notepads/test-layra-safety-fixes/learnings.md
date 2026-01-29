## 2026-01-29 Initialization
- Notepad initialized for plan `test-layra-safety-fixes`.

## 2026-01-29 MinIO public URL (presigned)
- `.env` change required: add `MINIO_PUBLIC_URL=http://localhost:9000` right after `MINIO_URL=http://minio:9000`.
- Important: `docker compose restart backend` does NOT reload env vars. Need recreate: `./scripts/compose-clean up -d --no-deps --force-recreate backend`.
- Verified in container: `docker exec layra-backend env | grep '^MINIO_PUBLIC_URL='` returned `MINIO_PUBLIC_URL=http://localhost:9000`.

## 2026-01-29 Port Conflict Resolution
- System minio.service occupies port 9000 on host.
- Solution: Changed docker-compose.yml port mapping from `9000:9000` to `9080:9000`.
- MINIO_PUBLIC_URL updated to `http://localhost:9080`.
- Internal container communication still uses `minio:9000` (unchanged).

## 2026-01-29 RAG Timing Validation
- RAG timing logs confirmed working with format: `RAG timings embed_s=X.XXX search_s=X.XXX meta_s=X.XXX minio_s=X.XXX hits=N total_s=X.XXX mode=rag`
- Embedding takes ~700ms per query.
- No vector deletions observed (safety fix working).
- No presigned URLs logged (security fix working).
