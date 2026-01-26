# Neo4j Integration for LAYRA (Future Scaling)

## Current Status
- **Configuration**: Reserved in `.env` (thesis mode) and `config.py`.
- **Infrastructure**: Docker image ready (`neo4j:5.15`).
- **Usage**: Not yet integrated into core RAG logic.
- **Purpose**: Knowledge graph representation for enhanced semantic reasoning and entity linking.

## Setup Instructions

### 1. Docker Compose
The `docker-compose.thesis.yml` includes the Neo4j service:

```yaml
neo4j:
  image: neo4j:5.15
  container_name: layra-neo4j
  environment:
    NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
  ports:
    - "7687:7687"  # Bolt protocol
    - "7474:7474"  # Web Interface
  networks:
    - layra-net
```

### 2. Environment Variables
Add these to your `.env` file:
```bash
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
```

### 3. Verification
Access the Neo4j Browser at `http://localhost:7474` and log in with your credentials.

---

## 🚀 Roadmap: Knowledge Graph Evolution

### Phase 1: Entity Extraction (Q2 2026)
*   **Goal**: Extract nodes (People, Organizations, Locations) from PDF text during ingestion.
*   **Tech**: Use LLM-based extraction nodes in Layra workflows.
*   **Storage**: Save extracted entities and their basic properties into Neo4j.

### Phase 2: Graph-Based Retrieval (Q3 2026)
*   **Goal**: Supplement Milvus vector search with graph traversals.
*   **Strategy**: "Retrieve-to-Graph" — after finding relevant chunks in Milvus, query Neo4j for related entities/concepts to expand context.

### Phase 3: Reasoning & Insights (Q4 2026)
*   **Goal**: Use Neo4j to explain "Why" documents are related.
*   **Feature**: Multi-hop reasoning (e.g., "Document A mentions Compound X, which is related to Herb Y in Document B").

---

## 🔧 Developer Notes (Implementation Prototype)

To implement the first connection, use the `neo4j` Python driver:

```python
# Proposed: backend/app/db/neo4j.py
from neo4j import AsyncGraphDatabase
from app.core.config import settings

class Neo4jManager:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

    async def close(self):
        await self.driver.close()

    async def create_entity(self, label: str, name: str):
        async with self.driver.session() as session:
            await session.run(
                f"MERGE (n:{label} {{name: $name}})",
                name=name
            )
```
