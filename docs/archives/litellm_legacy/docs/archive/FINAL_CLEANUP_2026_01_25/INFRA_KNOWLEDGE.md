# Infrastructure Knowledge Base (RAG)

This document describes an **optional** internal RAG system (pgvector-backed)
used in earlier iterations. In this repo snapshot, the only shipped refresh
tool is `bin/refresh_knowledge.sh`, which updates `docs/generated/` from a
running proxy. The pgvector ingestion/query scripts referenced in older docs
are **not present** here.

## 1. Architecture
- **Engine:** PostgreSQL `pgvector` (port from `DATABASE_URL`).
- **Table:** `infra_knowledge` (stores chunks, embeddings, and metadata).
- **Embedding Model:** `ollama/nomic-embed-text` (768 dimensions).
- **ID:** Managed in LiteLLM as `pg-internal`.

## 2. Ingested Content
The following "sources of truth" are indexed:
- `.env`: Environment variables and ports.
- `config.yaml`: Routing, fallbacks, and security settings.
- `schema.prisma`: Database structure.
- `docs/*.md`: Operational guides and maintenance reports.
- **Live State Snapshot**: A dynamically generated markdown file containing the active DB configuration (models, MCP servers, search tools).

## 3. Tooling (Current Repo)

### Refresh Generated Reports
To refresh `docs/generated/` from the running proxy:
```bash
./bin/refresh_knowledge.sh
```

### Optional RAG System (Not Shipped)
If you reintroduce the pgvector-based RAG system described above, you will
need to add ingestion and query tooling (e.g., `ingest_native_pg.py`,
`generate_and_ingest_state.py`, `query_infra.py`) along with the database
schema and scheduler.

## 4. Automation (Optional)
If you run periodic refreshes, schedule `bin/refresh_knowledge.sh` via cron or
your scheduler of choice.

## 5. Integration with Agents
The system uses the **`Infrastructure Guardian`** skill (System Prompt) which directs models to use the `pg-internal` vector store whenever a query about the local setup is detected.
