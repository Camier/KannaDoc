#!/usr/bin/env python3
"""Neo4j graph database ingestion for ethnopharmacology documents.

Two-phase ingestion pipeline:
  Phase 1: Document + Chunks from normalized.json
  Phase 2: Entities from entities.json

Uses MERGE operations for idempotent upserts.
Connects to Neo4j at bolt://localhost:7687 with NO AUTH and database "layra".
"""

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)

# Neo4j connection (NO AUTH)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "layra")
NEO4J_AUTH = None


def make_entity_id(entity_type: str, name: str) -> str:
    """Generate canonical entity ID from type and name.

    Args:
        entity_type: Entity type (e.g., 'Compound', 'Plant')
        name: Entity name (e.g., 'Curcumin')

    Returns:
        Normalized entity ID (e.g., 'compound_curcumin')
    """
    normalized = name.lower().replace(" ", "_").replace("-", "_")[:50]
    return f"{entity_type.lower()}_{normalized}"


def create_constraints(session) -> None:
    """Create unique constraints for Document, Chunk, and Entity nodes.

    Args:
        session: Neo4j session object
    """
    constraints = [
        "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
    ]

    for constraint in constraints:
        session.run(constraint)
        logger.info(f"[OK] Constraint created or exists: {constraint[:60]}...")


def ingest_document(session, normalized: dict[str, Any]) -> dict[str, int]:
    """Phase 1: Ingest Document and Chunks from normalized.json data.

    Creates Document node with metadata and Chunk nodes with text content.
    Links chunks to document via CONTAINS relationship.

    Args:
        session: Neo4j session object
        normalized: Parsed normalized.json dictionary

    Returns:
        Dict with counts: {'documents': 1, 'chunks': N}
    """
    doc_id = normalized.get("doc_id", normalized.get("id", ""))
    metadata = normalized.get("metadata", {})
    chunks = normalized.get("chunks", [])

    # MERGE Document node
    doc_cypher = """
    MERGE (d:Document {id: $doc_id})
    SET d.title = $title,
        d.year = $year,
        d.doi = $doi,
        d.source_path = $source_path
    RETURN d.id AS id
    """
    session.run(
        doc_cypher,
        {
            "doc_id": doc_id,
            "title": metadata.get("title", ""),
            "year": metadata.get("publication_year", metadata.get("year")),
            "doi": metadata.get("doi", ""),
            "source_path": normalized.get("source_path", ""),
        },
    )
    logger.info(f"[OK] MERGE Document: {doc_id}")

    # MERGE Chunks and relationships
    chunk_count = 0
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", chunk.get("id", ""))
        text = chunk.get("text", "")
        page_refs = chunk.get("page_refs", [])

        chunk_cypher = """
        MERGE (c:Chunk {id: $chunk_id})
        SET c.text = $text,
            c.page_refs = $page_refs,
            c.doc_id = $doc_id
        WITH c
        MATCH (d:Document {id: $doc_id})
        MERGE (d)-[:CONTAINS]->(c)
        RETURN c.id AS id
        """
        session.run(
            chunk_cypher,
            {
                "chunk_id": chunk_id,
                "text": text,
                "page_refs": page_refs,
                "doc_id": doc_id,
            },
        )
        chunk_count += 1

    logger.info(f"[OK] MERGE {chunk_count} Chunks for Document {doc_id}")
    return {"documents": 1, "chunks": chunk_count, "doc_id": doc_id}


def ingest_entities(session, doc_dir: Path, doc_id: str) -> dict[str, int]:
    """Phase 2: Ingest Entities + Relationships from entities.json (V3.1).

    Reads per-document entities.json file and creates Entity nodes.
    Links entities to chunks via MENTIONS and connects entity relationships.

    Args:
        session: Neo4j session object
        doc_dir: Path to document directory containing entities.json
        doc_id: Document identifier for logging

    Returns:
        Dict with counts: {'entities': N, 'mentions': M, 'relations': R}
    """
    entities_path = doc_dir / "entities.json"

    if not entities_path.exists():
        logger.warning(f"[SKIP] entities.json not found: {entities_path}")
        return {"entities": 0, "mentions": 0}

    with open(entities_path, "r", encoding="utf-8") as f:
        entities_data = json.load(f)

    entities = entities_data.get("entities", [])
    relationships = entities_data.get("relationships", [])

    entity_count = 0
    mention_count = 0
    relation_count = 0
    seen_entities = set()
    entity_id_map: dict[str, str] = {}

    for entity in entities:
        entity_type = (entity.get("type") or "").strip()
        source_id = (entity.get("id") or "").strip()
        name = (entity.get("name") or source_id or "unknown").strip()
        if not entity_type or not name:
            continue

        entity_id = make_entity_id(entity_type, name)
        if source_id:
            entity_id_map[source_id] = entity_id

        if entity_id not in seen_entities:
            entity_cypher = """
            MERGE (e:Entity {id: $entity_id})
            SET e.type = $entity_type,
                e.name = $entity_name
            RETURN e.id AS id
            """
            session.run(
                entity_cypher,
                {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "entity_name": name,
                },
            )
            seen_entities.add(entity_id)
            entity_count += 1

        for chunk_id in entity.get("source_chunk_ids", []) or []:
            mention_cypher = """
            MATCH (c:Chunk {id: $chunk_id})
            MATCH (e:Entity {id: $entity_id})
            MERGE (c)-[r:MENTIONS]->(e)
            SET r.evidence = $evidence,
                r.confidence = $confidence
            RETURN type(r) AS rel_type
            """
            session.run(
                mention_cypher,
                {
                    "chunk_id": chunk_id,
                    "entity_id": entity_id,
                    "evidence": entity.get("evidence", ""),
                    "confidence": entity.get("confidence"),
                },
            )
            mention_count += 1

    for rel in relationships:
        rel_type = (rel.get("type") or "").strip().upper()
        if not rel_type.replace("_", "").isalpha():
            continue

        source_id = entity_id_map.get(rel.get("source_entity_id", ""), "")
        target_id = entity_id_map.get(rel.get("target_entity_id", ""), "")
        if not source_id or not target_id:
            continue

        rel_cypher = f"""
        MATCH (a:Entity {{id: $source_id}})
        MATCH (b:Entity {{id: $target_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r.confidence = $confidence,
            r.evidence = $evidence,
            r.source_chunk_ids = $source_chunk_ids,
            r.attributes = $attributes,
            r.supporting_study_ids = $supporting_study_ids,
            r.verified = $verified
        RETURN type(r) AS rel_type
        """
        session.run(
            rel_cypher,
            {
                "source_id": source_id,
                "target_id": target_id,
                "confidence": rel.get("confidence"),
                "evidence": rel.get("evidence", ""),
                "source_chunk_ids": rel.get("source_chunk_ids", []),
                "attributes": rel.get("attributes", {}),
                "supporting_study_ids": rel.get("supporting_study_ids", []),
                "verified": rel.get("verified"),
            },
        )
        relation_count += 1

    logger.info(
        f"[OK] MERGE {entity_count} Entities, {mention_count} MENTIONS,"
        f" {relation_count} RELATIONSHIPS for doc {doc_id}"
    )
    return {
        "entities": entity_count,
        "mentions": mention_count,
        "relations": relation_count,
    }


def test_connection() -> bool:
    """Test Neo4j database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("RETURN 1 AS test")
            record = result.single()
            value = record["test"] if record else None
            success = value == 1
            print(f"Connection OK: {success}")
            driver.close()
            return success
    except Exception as e:
        print(f"Connection FAILED: {e}")
        return False


def ingest_directory(doc_dir: Path) -> dict[str, int]:
    """Ingest a complete document directory (both phases).

    Args:
        doc_dir: Path to document directory with normalized.json and optionally entities.json

    Returns:
        Combined counts from both phases
    """
    normalized_path = doc_dir / "normalized.json"

    if not normalized_path.exists():
        logger.error(f"[ERROR] normalized.json not found: {normalized_path}")
        return {"documents": 0, "chunks": 0, "entities": 0, "mentions": 0}

    with open(normalized_path, "r", encoding="utf-8") as f:
        normalized = json.load(f)

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            # Ensure constraints exist
            create_constraints(session)

            # Phase 1: Document + Chunks
            phase1 = ingest_document(session, normalized)

            # Phase 2: Entities (if available)
            doc_id = str(phase1.get("doc_id", ""))
            phase2 = ingest_entities(session, doc_dir, doc_id)

        return {**phase1, **phase2}
    finally:
        driver.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Neo4j graph database ingestion for ethnopharmacology documents."
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test Neo4j database connection and exit",
    )
    parser.add_argument(
        "--doc-dir", type=Path, help="Path to document directory with normalized.json"
    )
    parser.add_argument(
        "--create-constraints",
        action="store_true",
        help="Create database constraints and exit",
    )

    args = parser.parse_args()

    if args.test_connection:
        success = test_connection()
        exit(0 if success else 1)

    if args.create_constraints:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        with driver.session(database=NEO4J_DATABASE) as session:
            create_constraints(session)
        driver.close()
        print("Constraints created successfully")
        exit(0)

    if args.doc_dir:
        counts = ingest_directory(args.doc_dir)
        print(f"Ingestion complete: {counts}")
        exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
