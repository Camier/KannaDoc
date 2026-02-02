# Archived Python Scripts

This directory contains historical Python scripts that are no longer used in current workflows. They are preserved here for historical reference and to keep the active `scripts/` directory clean.

## Archived Scripts (2026-02-02)

### legacy_backfill_minio_images.py
- **Original Location:** `/scripts/legacy_backfill_minio_images.py`
- **Purpose:** Backfilling MinIO image storage for legacy data versions.
- **Reason for Archival:** Obsoleted by modern ingestion pipelines that handle image storage natively.

### sync_kb_metadata.py
- **Original Location:** `/scripts/sync_kb_metadata.py`
- **Purpose:** Synchronizing metadata between knowledge base versions.
- **Reason for Archival:** Functionality integrated into core management APIs.

### deduplicate_kb.py
- **Original Location:** `/scripts/deduplicate_kb.py`
- **Purpose:** Cleaning up duplicate entries in knowledge bases.
- **Reason for Archival:** Replaced by automated deduplication during ingestion and database unique constraints.

### hf_job_colqwen_test.py
- **Original Location:** `/scripts/hf_job_colqwen_test.py`
- **Purpose:** Testing ColQwen model jobs on Hugging Face infrastructure.
- **Reason for Archival:** Internal testing complete; logic migrated to CI/CD pipelines.

### cloud_ingest_heavy.py
- **Original Location:** `/scripts/cloud_ingest_heavy.py`
- **Purpose:** Heavy-duty ingestion specifically optimized for cloud environments.
- **Reason for Archival:** Consolidated into `ingest_sync.py` and other unified ingestion scripts.

### gpu_benchmark.py
- **Original Location:** `/scripts/gpu_benchmark.py`
- **Purpose:** Benchmarking GPU performance for embedding models.
- **Reason for Archival:** Replaced by standard monitoring tools and built-in metric tracking.
