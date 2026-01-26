# Neo4j Integration for Layra Thesis Deployment

## Overview

Neo4j is a native graph database that excels at managing highly connected data. In the context of a thesis deployment, Neo4j enables:

- **Knowledge Graphs**: Store and query relationships between entities
- **Workflow Traces**: Track execution paths and dependencies
- **Semantic Networks**: Model concept relationships for AI agents
- **Social Networks**: Analyze connections in multi-user scenarios

## ⚠️ Current Status: Infrastructure Ready, Application Integration Pending

| Component | Status | Notes |
|-----------|--------|-------|
| **Neo4j Service** | ✅ Running (in thesis mode only) | Container available at `bolt://neo4j:7687` |
| **Web UI (Browser)** | ✅ Accessible at `http://localhost:7474` | Username: `neo4j`, Password: from `NEO4J_PASSWORD` |
| **Python Driver** | ❌ Not installed | Missing from `requirements.txt` |
| **Configuration** | ✅ Environment variables defined | In `docker-compose.thesis.yml` and `.env.thesis` |
| **Application Code** | ❌ Not implemented | No Neo4j client or integration in backend |
| **Original LAYRA Release** | ❌ Not included | Neo4j is a thesis-specific addition |

### Summary
Neo4j is **fully configured at the infrastructure level** but **not yet integrated with the LAYRA application**. The database is running and accessible, but no application code currently stores or retrieves data from it. This documentation describes the **planned integration** for thesis use cases.

## Neo4j Service Configuration

### Docker Compose Service

```yaml
neo4j:
  container_name: layra-neo4j
  image: neo4j:5.23-community
  environment:
    - NEO4J_AUTH=neo4j/your_password
    - NEO4J_dbms_memory_heap_initial__size=512m
    - NEO4J_dbms_memory_heap_max__size=2G
    - NEO4J_dbms_memory_pagecache_size=1G
    - NEO4J_dbms_connector_bolt_advertised__address=:7687
    - NEO4J_dbms_connector_http_advertised__address=:7474
    - NEO4J_dbms_security_procedures_unrestricted=apoc.*
    - NEO4J_PLUGINS=["apoc"]
  volumes:
    - neo4j_data:/data
    - neo4j_logs:/logs
  ports:
    - "7474:7474"  # HTTP (Neo4j Browser)
    - "7687:7687"  # Bolt (Protocol)
```

### Memory Configuration

For thesis deployment (single machine):
- **Heap Memory**: 2GB (max)
- **Page Cache**: 1GB
- **Total RAM Impact**: ~3-4GB

## Access Points

### Neo4j Browser (Web UI)

```
URL: http://localhost:7474
Username: neo4j
Password: (from NEO4J_PASSWORD in .env.thesis)
```

**Features:**
- Visual graph exploration
- Cypher query editor with syntax highlighting
- Node and relationship visualization
- Query performance profiling

### Bolt Protocol (Application Access)

```
URI: bolt://neo4j:7687 (within Docker network)
     bolt://localhost:7687 (from host)
Username: neo4j
Password: (from NEO4J_PASSWORD)
```

## Python Integration

### Install Neo4j Driver

```bash
pip install neo4j
```

### Connection Example

```python
from neo4j import GraphDatabase

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self, cypher, parameters=None):
        with self.driver.session() as session:
            result = session.run(cypher, parameters)
            return [record for record in result]

# Usage (from backend container)
conn = Neo4jConnection(
    uri="bolt://neo4j:7687",
    user="neo4j",
    password="your_password"
)

# Create nodes
conn.query("""
    CREATE (w:Workflow {id: $workflow_id, name: $name, created_at: datetime()})
""", {"workflow_id": "wf_123", "name": "My Thesis Workflow"})

# Query nodes
result = conn.query("""
    MATCH (w:Workflow)
    RETURN w ORDER BY w.created_at DESC LIMIT 10
""")
```

## Common Use Cases for Thesis

### 1. Workflow Execution Graph

```cypher
// Create workflow execution trace
CREATE (wf:Workflow {id: 'wf_123'})
CREATE (n1:Node {id: 'node_1', type: 'code', status: 'completed'})
CREATE (n2:Node {id: 'node_2', type: 'vlm', status: 'running'})
CREATE (n3:Node {id: 'node_3', type: 'condition', status: 'pending'})
CREATE (wf)-[:HAS_NODE]->(n1)
CREATE (wf)-[:HAS_NODE]->(n2)
CREATE (wf)-[:HAS_NODE]->(n3)
CREATE (n1)-[:EXECUTES_BEFORE]->(n2)
CREATE (n2)-[:EXECUTES_BEFORE]->(n3)

// Query execution path
MATCH path = (wf:Workflow {id: 'wf_123'})-[:HAS_NODE*]->(n)
RETURN [node in nodes(path) | {id: node.id, type: node.type, status: node.status}]
```

### 2. Knowledge Graph for RAG

```cypher
// Create document-concept graph
CREATE (doc:Document {id: 'doc_123', title: 'Thesis Chapter 1'})
CREATE (c1:Concept {name: 'Machine Learning'})
CREATE (c2:Concept {name: 'Neural Networks'})
CREATE (c3:Concept {name: 'Deep Learning'})
CREATE (doc)-[:MENTIONS]->(c1)
CREATE (doc)-[:MENTIONS]->(c2)
CREATE (c1)-[:RELATED_TO]->(c3)
CREATE (c2)-[:IS_A]->(c3)

// Find related documents for RAG
MATCH (doc:Document {id: 'doc_123'})-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(related:Document)
RETURN DISTINCT related.title, count(c) as relevance
ORDER BY relevance DESC
```

### 3. Multi-Turn Conversation Context

```cypher
// Store conversation turns
CREATE (conv:Conversation {id: 'conv_123', user: 'thesis'})
CREATE (t1:Turn {role: 'user', content: 'What is ColQwen?', timestamp: datetime()})
CREATE (t2:Turn {role: 'assistant', content: 'ColQwen is...', timestamp: datetime()})
CREATE (conv)-[:HAS_TURN]->(t1)
CREATE (conv)-[:HAS_TURN]->(t2)
CREATE (t1)-[:FOLLOWS]->(t2)

// Retrieve conversation context
MATCH (conv:Conversation {id: 'conv_123'})-[:HAS_TURN]->(t:Turn)
RETURN t.role, t.content, t.timestamp
ORDER BY t.timestamp ASC
```

### 4. Entity Relationship Extraction

```cypher
// Store extracted entities from documents
CREATE (doc:Document {id: 'doc_456'})
CREATE (e1:Entity {name: 'Layra', type: 'Organization'})
CREATE (e2:Entity {name: 'ColQwen', type: 'Technology'})
CREATE (e3:Entity {name: 'Visual RAG', type: 'Method'})
CREATE (doc)-[:CONTAINS_ENTITY]->(e1)
CREATE (doc)-[:CONTAINS_ENTITY]->(e2)
CREATE (doc)-[:CONTAINS_ENTITY]->(e3)
CREATE (e1)-[:USES]->(e2)
CREATE (e2)-[:IMPLEMENTS]->(e3)

// Query entity relationships
MATCH path = (e1:Entity)-[:USES|IMPLEMENTS*1..3]-(e2:Entity)
WHERE e1.name = 'Layra'
RETURN DISTINCT e2.name, e2.type
```

## Advanced Patterns

### Time-Series Data

```cypher
// Track workflow metrics over time
CREATE (m:Metric {
    workflow_id: 'wf_123',
    timestamp: datetime(),
    cpu_usage: 45.2,
    memory_usage: 2.1,
    execution_time: 1234
})

// Query time-series data
MATCH (m:Metric {workflow_id: 'wf_123'})
WHERE m.timestamp > datetime() - duration('P1D')
RETURN m.timestamp, m.cpu_usage, m.memory_usage
ORDER BY m.timestamp ASC
```

### Graph Algorithms (via APOC)

```cypher
// Find shortest path between nodes
MATCH (start:Node {id: 'node_1'}), (end:Node {id: 'node_10'})
CALL apoc.algo.shortestPath(start, end, 'EXECUTES_BEFORE', 1.0)
YIELD path, weight
RETURN [node in nodes(path) | node.id] as execution_path

// PageRank for node importance
CALL apoc.algo.pageRankStats({
    nodeProjection: 'Node',
    relationshipProjection: 'EXECUTES_BEFORE'
})
YIELD node, score
RETURN node.id, node.type, score
ORDER BY score DESC
LIMIT 10
```

### Batch Operations

```python
# Python: Batch insert workflow nodes
def batch_create_nodes(driver, workflow_id, nodes):
    with driver.session() as session:
        session.run("""
            UNWIND $nodes AS node
            MERGE (n:Node {id: node.id})
            SET n.type = node.type,
                n.status = node.status,
                n.workflow_id = $workflow_id,
                n.created_at = datetime()
        """, workflow_id=workflow_id, nodes=nodes)

# Usage
nodes = [
    {"id": "n1", "type": "code", "status": "pending"},
    {"id": "n2", "type": "vlm", "status": "pending"},
    {"id": "n3", "type": "condition", "status": "pending"}
]
batch_create_nodes(driver, "wf_123", nodes)
```

## Monitoring & Maintenance

### Check Database Size

```bash
# Neo4j container
docker exec layra-neo4j du -sh /data
docker exec layra-neo4j du -sh /logs
```

### Query Performance

```cypher
// Enable profiling
PROFILE MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100

// Check query plan
EXPLAIN MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100
```

### Backup & Restore

```bash
# Backup (from neo4j container)
docker exec layra-neo4j neo4j-admin database dump neo4j --to-path=/backups

# Restore
docker exec layra-neo4j neo4j-admin database load neo4j --from-path=/backups --force
```

## Integration with Layra Services

### Backend Integration Points

Add to `backend/app/core/config.py`:
```python
# Neo4j Configuration
NEO4J_URI: str = "bolt://neo4j:7687"
NEO4J_USER: str = "neo4j"
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD")
```

Create `backend/app/db/neo4j.py`:
```python
from neo4j import GraphDatabase
from backend.app.core.config import settings

class Neo4jClient:
    _instance = None

    @classmethod
    def get_client(cls):
        if cls._instance is None:
            cls._instance = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
        return cls._instance
```

### Workflow Engine Integration

```python
# In workflow_engine.py - save execution graph to Neo4j
async def save_execution_graph(self):
    client = Neo4jClient.get_client()

    # Create workflow node
    with client.session() as session:
        session.run("""
            CREATE (wf:WorkflowExecution {
                id: $task_id,
                username: $username,
                started_at: datetime(),
                status: 'running'
            })
        """, task_id=self.task_id, username=self.username)

        # Create node relationships
        for node in self.nodes:
            session.run("""
                MATCH (wf:WorkflowExecution {id: $task_id})
                CREATE (n:WorkflowNode {
                    id: $node_id,
                    type: $node_type,
                    status: 'pending'
                })
                CREATE (wf)-[:HAS_NODE]->(n)
            """, task_id=self.task_id, node_id=node.node_id, node_type=node.node_type)
```

## Troubleshooting

### Connection Issues

```bash
# Check if Neo4j is accessible from backend
docker exec layra-backend curl -f http://neo4j:7474

# Check Bolt connection
docker exec layra-backend nc -zv neo4j 7687
```

### Memory Issues

```bash
# Check Neo4j memory usage
docker exec layra-neo4j neo4j-admin server report

# Adjust memory in docker-compose.thesis.yml if needed
```

### Slow Queries

```cypher
// Find slow queries
CALL dbms.listQueries()
YIELD queryId, query, runtimeMillis
WHERE runtimeMillis > 1000
RETURN queryId, query, runtimeMillis
ORDER BY runtimeMillis DESC
```

## Resources

- **Neo4j Documentation**: https://neo4j.com/docs/
- **Cypher Query Language**: https://neo4j.com/docs/cypher-manual/
- **APOC Procedure Library**: https://neo4j.com/labs/apoc/5/
- **Python Driver**: https://neo4j.com/docs/python-manual/
