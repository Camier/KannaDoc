#!/usr/bin/env python3
"""
Milvus Ingestion Script for RAG-Optimized Chunks

This script ingests RAG-optimized chunks into a Milvus vector database.
Supports batch insertion, duplicate detection, and progress tracking.

Usage:
    python3 scripts/milvus_ingest.py chunks.jsonl [--collection NAME] [--milvus-host HOST] [--batch-size N]

Requirements:
    - pymilvus>=2.3.0
    - OpenAI API key for embeddings (text-embedding-ada-002)
    - Running Milvus server (default: localhost:19530)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator
from dataclasses import dataclass, asdict
import hashlib

# Optional imports with graceful degradation
try:
    from pymilvus import (
        connections,
        utility,
        FieldSchema,
        CollectionSchema,
        DataType,
        Collection,
        MilvusException,
    )

    # AnnInsertNotSuccessError may not exist in all versions
    try:
        from pymilvus import AnnInsertNotSuccessError
    except ImportError:
        AnnInsertNotSuccessError = MilvusException

    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_COLLECTION = "ethnopharmacology_v2"
DEFAULT_MILVUS_HOST = "localhost"
DEFAULT_MILVUS_PORT = 19530
DEFAULT_BATCH_SIZE = 100
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072

# Ollama embedding support (fallback when OpenAI quota exceeded)
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text:latest"
OLLAMA_EMBEDDING_DIM = 768

# Global embedding provider flag (set via CLI)
USE_OLLAMA_EMBEDDINGS = False

# Milvus Collection Schema
FIELD_ID = "id"
FIELD_TEXT = "text"
FIELD_EMBEDDING = "embedding"
FIELD_DOC_ID = "doc_id"
FIELD_DOC_TITLE = "doc_title"
FIELD_AUTHORS = "authors"
FIELD_YEAR = "year"
FIELD_DOI = "doi"
FIELD_PAGE = "page"
FIELD_SECTION = "section"
FIELD_KEY_ENTITIES = "key_entities"
FIELD_CHUNK_TYPE = "chunk_type"
FIELD_CHAR_COUNT = "char_count"

# V2 Schema Fields (normalized mode)
FIELD_V2_CHUNK_ID = "chunk_id"
FIELD_V2_TEXT = "text"
FIELD_V2_EMBEDDING = "embedding"
FIELD_V2_DOC_ID = "doc_id"
FIELD_V2_PAGE_REFS = "page_refs"
FIELD_V2_BLOCK_IDS = "block_ids"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class PaperMetadata:
    """Metadata for a paper."""

    paper_id: str
    citekey: str
    kind: str
    title: str
    authors: List[str]
    year: int
    doi: Optional[str]
    isbn: Optional[str]
    issn: Optional[str]
    container_title: Optional[str]
    publisher: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    pages: Optional[str]
    edition: Optional[str]
    identifiers: Optional[Dict[str, Any]]


@dataclass
class Chunk:
    """RAG-optimized chunk for Milvus ingestion."""

    id: str
    text: str
    doc_id: str
    doc_title: str
    authors: List[str]
    year: int
    doi: Optional[str]
    page: int
    section: str
    key_entities: List[str]
    chunk_type: str
    char_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to Milvus-compatible dict."""
        return {
            FIELD_ID: self.id,
            FIELD_TEXT: self.text,
            FIELD_DOC_ID: self.doc_id,
            FIELD_DOC_TITLE: self.doc_title,
            FIELD_AUTHORS: json.dumps(self.authors),
            FIELD_YEAR: self.year,
            FIELD_DOI: self.doi or "",
            FIELD_PAGE: self.page,
            FIELD_SECTION: self.section,
            FIELD_KEY_ENTITIES: json.dumps(self.key_entities),
            FIELD_CHUNK_TYPE: self.chunk_type,
            FIELD_CHAR_COUNT: self.char_count,
        }


@dataclass
class IngestStats:
    """Statistics for ingestion process."""

    total_chunks: int = 0
    successful: int = 0
    failed: int = 0
    duplicates: int = 0
    batches: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration(self) -> float:
        return (
            self.end_time - self.start_time
            if self.end_time > 0
            else time.time() - self.start_time
        )

    @property
    def success_rate(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.successful / self.total_chunks) * 100


# ============================================================================
# Milvus Connection and Schema Management
# ============================================================================


def connect_milvus(
    host: str = DEFAULT_MILVUS_HOST, port: int = DEFAULT_MILVUS_PORT
) -> bool:
    """
    Connect to Milvus server.

    Args:
        host: Milvus server host
        port: Milvus server port

    Returns:
        True if connection successful, False otherwise
    """
    if not MILVUS_AVAILABLE:
        print(
            "ERROR: pymilvus library not installed. Install with: pip install pymilvus"
        )
        return False

    try:
        connections.connect("default", host=host, port=port)
        print(f"Connected to Milvus at {host}:{port}")
        return True
    except MilvusException as e:
        print(f"ERROR: Failed to connect to Milvus at {host}:{port}")
        print(f"Details: {e}")
        print("\nTroubleshooting:")
        print(
            "  1. Ensure Milvus is running: docker-compose up -d (or milvus standalone)"
        )
        print("  2. Check host/port configuration")
        print("  3. Verify firewall settings")
        return False


def disconnect_milvus() -> None:
    """Disconnect from Milvus server."""
    try:
        connections.disconnect("default")
        print("Disconnected from Milvus")
    except Exception:
        pass


def create_collection_schema() -> CollectionSchema:
    """
    Create the collection schema for ethnopharmacology papers.

    Returns:
        CollectionSchema object
    """
    fields = [
        FieldSchema(
            name=FIELD_ID,
            dtype=DataType.VARCHAR,
            max_length=255,
            is_primary=True,
            auto_id=False,
        ),
        FieldSchema(name=FIELD_TEXT, dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(
            name=FIELD_EMBEDDING, dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM
        ),
        FieldSchema(name=FIELD_DOC_ID, dtype=DataType.VARCHAR, max_length=255),
        FieldSchema(name=FIELD_DOC_TITLE, dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name=FIELD_AUTHORS, dtype=DataType.VARCHAR, max_length=2048),
        FieldSchema(name=FIELD_YEAR, dtype=DataType.INT64),
        FieldSchema(name=FIELD_DOI, dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name=FIELD_PAGE, dtype=DataType.INT64),
        FieldSchema(name=FIELD_SECTION, dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name=FIELD_KEY_ENTITIES, dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name=FIELD_CHUNK_TYPE, dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name=FIELD_CHAR_COUNT, dtype=DataType.INT64),
    ]

    return CollectionSchema(
        fields=fields, description="Ethnopharmacology papers RAG chunks"
    )


def create_v2_collection_schema() -> CollectionSchema:
    """
    Create the V2 collection schema for normalized chunks.

    Schema fields:
        - chunk_id (VARCHAR, 64, PRIMARY KEY)
        - embedding (FLOAT_VECTOR, 3072)
        - text (VARCHAR, 65535)
        - doc_id (VARCHAR, 64)
        - page_refs (VARCHAR, 256) - JSON array string
        - block_ids (VARCHAR, 1024) - JSON array string

    Returns:
        CollectionSchema object
    """
    fields = [
        FieldSchema(
            name=FIELD_V2_CHUNK_ID,
            dtype=DataType.VARCHAR,
            max_length=64,
            is_primary=True,
            auto_id=False,
        ),
        FieldSchema(
            name=FIELD_V2_EMBEDDING, dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM
        ),
        FieldSchema(name=FIELD_V2_TEXT, dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name=FIELD_V2_DOC_ID, dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name=FIELD_V2_PAGE_REFS, dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name=FIELD_V2_BLOCK_IDS, dtype=DataType.VARCHAR, max_length=1024),
    ]

    return CollectionSchema(
        fields=fields, description="Ethnopharmacology V2 normalized chunks"
    )


def create_collection_if_not_exists(
    collection_name: str, index_type: str = "HNSW", metric_type: str = "COSINE"
) -> Optional[Collection]:
    """
    Create Milvus collection with schema if it doesn't exist.

    Args:
        collection_name: Name of the collection
        index_type: Type of vector index (HNSW, IVF_FLAT, etc.)
        metric_type: Distance metric type (COSINE, L2, IP)

    Returns:
        Collection object or None if creation failed
    """
    if not MILVUS_AVAILABLE:
        return None

    try:
        # Check if collection exists
        if utility.has_collection(collection_name):
            print(f"Collection '{collection_name}' already exists")
            collection = Collection(collection_name)
            print(f"  - Loaded collection: {collection.num_entities} entities")
            return collection

        # Create schema
        schema = create_collection_schema()
        print(f"Creating collection '{collection_name}' with schema:")
        print(f"  - Index type: {index_type}")
        print(f"  - Metric type: {metric_type}")
        print(f"  - Embedding dim: {EMBEDDING_DIM}")

        # Create collection
        collection = Collection(name=collection_name, schema=schema)

        # Create index on embedding field
        index_params = {
            "index_type": index_type,
            "metric_type": metric_type,
            "params": {
                "M": 16,  # HNSW: number of bidirectional links
                "ef_construction": 200,  # HNSW: depth during construction
            },
        }

        print(f"Creating index on '{FIELD_EMBEDDING}' field...")
        collection.create_index(field_name=FIELD_EMBEDDING, index_params=index_params)

        print(f"Successfully created collection '{collection_name}'")
        return collection

    except MilvusException as e:
        print(f"ERROR: Failed to create collection '{collection_name}'")
        print(f"Details: {e}")
        return None


def create_v2_collection_if_not_exists(
    collection_name: str, index_type: str = "HNSW", metric_type: str = "COSINE"
) -> Optional[Collection]:
    """
    Create Milvus V2 collection with normalized schema if it doesn't exist.

    Args:
        collection_name: Name of the collection
        index_type: Type of vector index (HNSW, IVF_FLAT, etc.)
        metric_type: Distance metric type (COSINE, L2, IP)

    Returns:
        Collection object or None if creation failed
    """
    if not MILVUS_AVAILABLE:
        return None

    try:
        # Check if collection exists
        if utility.has_collection(collection_name):
            print(f"Collection '{collection_name}' already exists")
            collection = Collection(collection_name)
            print(f"  - Loaded collection: {collection.num_entities} entities")
            return collection

        # Create V2 schema
        schema = create_v2_collection_schema()
        print(f"Creating V2 collection '{collection_name}' with schema:")
        print(f"  - Index type: {index_type}")
        print(f"  - Metric type: {metric_type}")
        print(f"  - Embedding dim: {EMBEDDING_DIM}")

        # Create collection
        collection = Collection(name=collection_name, schema=schema)

        # Create index on embedding field
        index_params = {
            "index_type": index_type,
            "metric_type": metric_type,
            "params": {
                "M": 16,  # HNSW: number of bidirectional links
                "ef_construction": 200,  # HNSW: depth during construction
            },
        }

        print(f"Creating index on '{FIELD_V2_EMBEDDING}' field...")
        collection.create_index(
            field_name=FIELD_V2_EMBEDDING, index_params=index_params
        )

        print(f"Successfully created V2 collection '{collection_name}'")
        return collection

    except MilvusException as e:
        print(f"ERROR: Failed to create V2 collection '{collection_name}'")
        print(f"Details: {e}")
        return None


def load_collection(collection: Collection) -> bool:
    """
    Load collection into memory for search.

    Args:
        collection: Collection object

    Returns:
        True if successful, False otherwise
    """
    try:
        collection.load()
        print(f"Collection '{collection.name}' loaded into memory")
        return True
    except MilvusException as e:
        print(f"WARNING: Could not load collection into memory")
        print(f"Details: {e}")
        return False


# ============================================================================
# Embedding Generation
# ============================================================================


def generate_embedding(
    text: str, api_key: Optional[str] = None
) -> Optional[List[float]]:
    """
    Generate OpenAI ada-002 embedding for text.

    Args:
        text: Text to embed
        api_key: OpenAI API key (or use OPENAI_API_KEY env var)

    Returns:
        Embedding vector (1536 dim) or None if failed
    """
    if not OPENAI_AVAILABLE:
        print("ERROR: openai library not installed. Install with: pip install openai")
        return None

    # Get API key from parameter or environment
    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print(
            "ERROR: OpenAI API key not found. Set OPENAI_API_KEY environment variable."
        )
        return None

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return response.data[0].embedding
    except Exception as e:
        print(f"ERROR: Failed to generate embedding: {e}")
        return None


def generate_embeddings_batch(
    texts: List[str], api_key: Optional[str] = None
) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts in batch (more efficient).

    Args:
        texts: List of texts to embed
        api_key: OpenAI API key

    Returns:
        List of embedding vectors (1536 dim each)
    """
    # Use Ollama if flag is set
    if USE_OLLAMA_EMBEDDINGS:
        return generate_ollama_embeddings_batch(texts)

    if not OPENAI_AVAILABLE:
        return [None] * len(texts)

    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("ERROR: OpenAI API key not found.")
        return [None] * len(texts)

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        # Sort by index since API might return out of order
        embeddings = [None] * len(texts)
        for item in response.data:
            embeddings[item.index] = item.embedding
        return embeddings
    except Exception as e:
        print(f"ERROR: Failed to generate batch embeddings: {e}")
        return [None] * len(texts)


def generate_ollama_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using Ollama local model."""
    import requests

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={"model": OLLAMA_EMBEDDING_MODEL, "prompt": text},
            timeout=60,
        )
        response.raise_for_status()
        return response.json().get("embedding")
    except Exception as e:
        print(f"ERROR: Failed to generate Ollama embedding: {e}")
        return None


def generate_ollama_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """Generate embeddings for multiple texts using Ollama (sequential since no batch API)."""
    import requests

    embeddings = []
    for i, text in enumerate(texts):
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": OLLAMA_EMBEDDING_MODEL, "prompt": text},
                timeout=60,
            )
            response.raise_for_status()
            embeddings.append(response.json().get("embedding"))
        except Exception as e:
            if i == 0:  # Only print once
                print(f"ERROR: Ollama embedding failed: {e}")
            embeddings.append(None)
    return embeddings


# ============================================================================
# Chunk Processing
# ============================================================================


def generate_chunk_id(doc_id: str, page: int, section: str, chunk_index: int) -> str:
    """
    Generate a unique chunk ID.

    Args:
        doc_id: Document identifier
        page: Page number
        section: Section name
        chunk_index: Chunk index within document

    Returns:
        Unique chunk ID
    """
    unique_string = f"{doc_id}_{page}_{section}_{chunk_index}"
    hash_obj = hashlib.md5(unique_string.encode())
    return f"chunk_{hash_obj.hexdigest()}"


def load_paper_catalog(catalog_path: Path) -> Dict[str, PaperMetadata]:
    """
    Load paper catalog from JSONL file.

    Args:
        catalog_path: Path to paper_catalog.jsonl

    Returns:
        Dictionary mapping paper_id to PaperMetadata
    """
    catalog = {}
    if not catalog_path.exists():
        print(f"WARNING: Paper catalog not found at {catalog_path}")
        return catalog

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    paper = json.loads(line)
                    metadata = PaperMetadata(**paper)
                    catalog[metadata.paper_id] = metadata
        print(f"Loaded {len(catalog)} papers from catalog")
    except Exception as e:
        print(f"WARNING: Failed to load paper catalog: {e}")

    return catalog


def read_chunks(chunks_file: Path) -> Generator[Dict[str, Any], None, None]:
    """
    Read chunks from JSONL file.

    Args:
        chunks_file: Path to chunks JSONL file

    Yields:
        Chunk dictionaries
    """
    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")

    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def ingest_from_normalized(ext_dir: Path) -> Generator[Dict[str, Any], None, None]:
    """
    Read chunks from normalized.json file in extraction directory.

    Args:
        ext_dir: Path to extraction directory containing normalized.json

    Yields:
        Chunk dictionaries with V2 schema fields
    """
    normalized_file = ext_dir / "normalized.json"
    if not normalized_file.exists():
        raise FileNotFoundError(f"Normalized file not found: {normalized_file}")

    with open(normalized_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for chunk in data.get("chunks", []):
        yield {
            "text": chunk["text"],
            "doc_id": chunk["doc_id"],
            "chunk_id": chunk["chunk_id"],
            "page_refs": json.dumps(chunk.get("page_refs", [])),
            "block_ids": json.dumps(chunk.get("block_ids", [])),
        }


def prepare_chunk(
    chunk_data: Dict[str, Any],
    paper_metadata: Optional[PaperMetadata],
    chunk_index: int,
) -> Optional[Chunk]:
    """
    Prepare a chunk for Milvus ingestion.

    Args:
        chunk_data: Raw chunk data from JSONL
        paper_metadata: Paper metadata from catalog
        chunk_index: Sequential chunk index

    Returns:
        Chunk object or None if invalid
    """
    try:
        # Extract text content
        text = chunk_data.get("text", "").strip()
        if not text:
            return None

        # Get paper metadata
        paper_id = chunk_data.get("paper_name", "")
        if paper_metadata:
            doc_title = paper_metadata.title
            authors = paper_metadata.authors or []
            year = paper_metadata.year or 0
            doi = paper_metadata.doi
        else:
            # Fallback to chunk data
            doc_title = chunk_data.get("doc_title", paper_id)
            authors = chunk_data.get("authors", [])
            year = chunk_data.get("year", 0)
            doi = chunk_data.get("doi")

        # Extract page information
        page_start = chunk_data.get("page_start", 0)
        page_end = chunk_data.get("page_end", page_start)
        page = page_start

        # Section and chunk type
        section = chunk_data.get("section", "unknown")
        chunk_type = chunk_data.get("chunk_type", "text")

        # Key entities (if available)
        key_entities = chunk_data.get("key_entities", chunk_data.get("entities", []))
        if isinstance(key_entities, str):
            key_entities = [key_entities]

        # Generate unique ID
        chunk_id = generate_chunk_id(paper_id, page, section, chunk_index)

        return Chunk(
            id=chunk_id,
            text=text,
            doc_id=paper_id,
            doc_title=doc_title,
            authors=authors,
            year=year,
            doi=doi,
            page=page,
            section=section,
            key_entities=key_entities,
            chunk_type=chunk_type,
            char_count=len(text),
        )
    except Exception as e:
        print(f"WARNING: Failed to prepare chunk: {e}")
        return None


# ============================================================================
# Milvus Insertion
# ============================================================================


def check_existing_ids(collection: Collection, chunk_ids: List[str]) -> set:
    """
    Check which chunk IDs already exist in the collection.

    Args:
        collection: Milvus collection
        chunk_ids: List of chunk IDs to check

    Returns:
        Set of existing chunk IDs
    """
    try:
        # Query for existing IDs
        # Note: This is a simplified check. For large collections,
        # consider using a bloom filter or secondary index.
        existing = set()

        # Batch query to avoid hitting limits
        batch_size = 1000
        for i in range(0, len(chunk_ids), batch_size):
            batch = chunk_ids[i : i + batch_size]
            ids_str = ", ".join([f'"{id_}"' for id_ in batch])

            try:
                results = collection.query(
                    expr=f"{FIELD_ID} in [{ids_str}]", output_fields=[FIELD_ID]
                )
                existing.update(r[FIELD_ID] for r in results)
            except MilvusException:
                # If query fails, assume none exist (conservative)
                pass

        return existing
    except Exception as e:
        print(f"WARNING: Failed to check existing IDs: {e}")
        return set()


def insert_batch(
    collection: Collection,
    chunks: List[Chunk],
    embeddings: List[List[float]],
    stats: IngestStats,
) -> int:
    """
    Insert a batch of chunks into Milvus.

    Args:
        collection: Milvus collection
        chunks: List of chunks to insert
        embeddings: List of embedding vectors
        stats: Ingestion statistics object

    Returns:
        Number of successfully inserted chunks
    """
    if not chunks or not embeddings:
        return 0

    # Check for duplicates
    chunk_ids = [c.id for c in chunks]
    existing_ids = check_existing_ids(collection, chunk_ids)

    # Filter out duplicates
    new_chunks = []
    new_embeddings = []
    for chunk, emb in zip(chunks, embeddings):
        if chunk.id in existing_ids:
            stats.duplicates += 1
        else:
            new_chunks.append(chunk)
            new_embeddings.append(emb)

    if not new_chunks:
        return 0

    # Prepare data for insertion
    data = {
        FIELD_ID: [c.id for c in new_chunks],
        FIELD_TEXT: [c.text for c in new_chunks],
        FIELD_EMBEDDING: new_embeddings,
        FIELD_DOC_ID: [c.doc_id for c in new_chunks],
        FIELD_DOC_TITLE: [c.doc_title for c in new_chunks],
        FIELD_AUTHORS: [json.dumps(c.authors) for c in new_chunks],
        FIELD_YEAR: [c.year for c in new_chunks],
        FIELD_DOI: [c.doi or "" for c in new_chunks],
        FIELD_PAGE: [c.page for c in new_chunks],
        FIELD_SECTION: [c.section for c in new_chunks],
        FIELD_KEY_ENTITIES: [json.dumps(c.key_entities) for c in new_chunks],
        FIELD_CHUNK_TYPE: [c.chunk_type for c in new_chunks],
        FIELD_CHAR_COUNT: [c.char_count for c in new_chunks],
    }

    try:
        # Insert into Milvus
        insert_result = collection.insert(data=data)
        inserted_count = insert_result.insert_count
        stats.successful += inserted_count
        return inserted_count
    except (MilvusException, AnnInsertNotSuccessError) as e:
        print(f"ERROR: Failed to insert batch: {e}")
        stats.failed += len(new_chunks)
        return 0


def ingest_chunks(
    chunks_file: Path,
    collection: Collection,
    paper_catalog_path: Optional[Path] = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    api_key: Optional[str] = None,
    dry_run: bool = False,
) -> IngestStats:
    """
    Ingest chunks from JSONL file into Milvus.

    Args:
        chunks_file: Path to chunks JSONL file
        collection: Milvus collection object
        paper_catalog_path: Path to paper catalog JSONL
        batch_size: Number of chunks per batch
        api_key: OpenAI API key
        dry_run: If True, don't actually insert into Milvus

    Returns:
        Ingestion statistics
    """
    stats = IngestStats()
    stats.start_time = time.time()

    # Load paper catalog
    paper_catalog = {}
    if paper_catalog_path and paper_catalog_path.exists():
        paper_catalog = load_paper_catalog(paper_catalog_path)

    # Prepare batches
    chunk_batch = []
    texts_batch = []
    chunk_index = 0

    print(f"\nIngesting chunks from: {chunks_file}")
    print(f"Batch size: {batch_size}")
    if dry_run:
        print("DRY RUN MODE - No actual insertion")
    print()

    for raw_chunk in read_chunks(chunks_file):
        stats.total_chunks += 1

        # Get paper metadata
        paper_id = raw_chunk.get("paper_name", "")
        paper_metadata = paper_catalog.get(paper_id)

        # Prepare chunk
        chunk = prepare_chunk(raw_chunk, paper_metadata, chunk_index)
        if chunk is None:
            stats.failed += 1
            continue

        chunk_batch.append(chunk)
        texts_batch.append(chunk.text)
        chunk_index += 1

        # Process batch when full
        if len(chunk_batch) >= batch_size:
            stats.batches += 1
            print(
                f"Processing batch {stats.batches} ({len(chunk_batch)} chunks)...",
                end=" ",
                flush=True,
            )

            # Generate embeddings
            embeddings = generate_embeddings_batch(texts_batch, api_key)

            if all(emb is not None for emb in embeddings):
                # Filter out failed embeddings
                valid_chunks = []
                valid_embeddings = []
                for c, emb in zip(chunk_batch, embeddings):
                    if emb is not None:
                        valid_chunks.append(c)
                        valid_embeddings.append(emb)
                    else:
                        stats.failed += 1

                if not dry_run:
                    inserted = insert_batch(
                        collection, valid_chunks, valid_embeddings, stats
                    )
                    print(f"Inserted: {inserted}, Duplicates: {stats.duplicates}")
                else:
                    print(f"Would insert: {len(valid_chunks)} (DRY RUN)")
                    stats.successful += len(valid_chunks)
            else:
                print(f"Failed to generate embeddings for all chunks")
                stats.failed += len(chunk_batch)

            # Reset batch
            chunk_batch = []
            texts_batch = []

    # Process remaining chunks
    if chunk_batch:
        stats.batches += 1
        print(
            f"Processing final batch {stats.batches} ({len(chunk_batch)} chunks)...",
            end=" ",
            flush=True,
        )

        embeddings = generate_embeddings_batch(texts_batch, api_key)

        if all(emb is not None for emb in embeddings):
            valid_chunks = []
            valid_embeddings = []
            for c, emb in zip(chunk_batch, embeddings):
                if emb is not None:
                    valid_chunks.append(c)
                    valid_embeddings.append(emb)
                else:
                    stats.failed += 1

            if not dry_run:
                inserted = insert_batch(
                    collection, valid_chunks, valid_embeddings, stats
                )
                print(f"Inserted: {inserted}, Duplicates: {stats.duplicates}")
            else:
                print(f"Would insert: {len(valid_chunks)} (DRY RUN)")
                stats.successful += len(valid_chunks)
        else:
            print(f"Failed to generate embeddings for all chunks")
            stats.failed += len(chunk_batch)

    # Flush collection to ensure data is persisted
    if not dry_run and stats.successful > 0:
        try:
            collection.flush()
            print("\nFlushed collection to disk")
        except MilvusException as e:
            print(f"\nWARNING: Failed to flush collection: {e}")

    stats.end_time = time.time()
    return stats


def insert_v2_batch(
    collection: Collection,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    stats: IngestStats,
) -> int:
    """
    Insert a batch of V2 normalized chunks into Milvus.

    Args:
        collection: Milvus collection
        chunks: List of chunk dicts from ingest_from_normalized
        embeddings: List of embedding vectors
        stats: Ingestion statistics object

    Returns:
        Number of successfully inserted chunks
    """
    if not chunks or not embeddings:
        return 0

    # Check for duplicates
    chunk_ids = [c["chunk_id"] for c in chunks]
    existing_ids = check_v2_existing_ids(collection, chunk_ids)

    # Filter out duplicates
    new_chunks = []
    new_embeddings = []
    for chunk, emb in zip(chunks, embeddings):
        if chunk["chunk_id"] in existing_ids:
            stats.duplicates += 1
        else:
            new_chunks.append(chunk)
            new_embeddings.append(emb)

    if not new_chunks:
        return 0

    # Prepare data for insertion (column-based format - list of lists)
    data = [
        [c["chunk_id"] for c in new_chunks],  # chunk_id
        new_embeddings,  # embedding
        [c["text"] for c in new_chunks],  # text
        [c["doc_id"] for c in new_chunks],  # doc_id
        [c["page_refs"] for c in new_chunks],  # page_refs
        [c["block_ids"] for c in new_chunks],  # block_ids
    ]

    try:
        # Insert into Milvus
        insert_result = collection.insert(data=data)
        inserted_count = insert_result.insert_count
        stats.successful += inserted_count
        return inserted_count
    except (MilvusException, AnnInsertNotSuccessError) as e:
        print(f"ERROR: Failed to insert V2 batch: {e}")
        stats.failed += len(new_chunks)
        return 0


def check_v2_existing_ids(collection: Collection, chunk_ids: List[str]) -> set:
    """
    Check which V2 chunk IDs already exist in the collection.

    Args:
        collection: Milvus collection
        chunk_ids: List of chunk IDs to check

    Returns:
        Set of existing chunk IDs
    """
    try:
        existing = set()

        # Batch query to avoid hitting limits
        batch_size = 1000
        for i in range(0, len(chunk_ids), batch_size):
            batch = chunk_ids[i : i + batch_size]
            ids_str = ", ".join([f'"{id_}"' for id_ in batch])

            try:
                results = collection.query(
                    expr=f"{FIELD_V2_CHUNK_ID} in [{ids_str}]",
                    output_fields=[FIELD_V2_CHUNK_ID],
                )
                existing.update(r[FIELD_V2_CHUNK_ID] for r in results)
            except MilvusException:
                # If query fails, assume none exist (conservative)
                pass

        return existing
    except Exception as e:
        print(f"WARNING: Failed to check existing V2 IDs: {e}")
        return set()


def ingest_normalized_chunks(
    ext_dir: Path,
    collection: Collection,
    batch_size: int = DEFAULT_BATCH_SIZE,
    api_key: Optional[str] = None,
    dry_run: bool = False,
) -> IngestStats:
    """
    Ingest chunks from normalized.json file into Milvus V2 collection.

    Args:
        ext_dir: Path to extraction directory containing normalized.json
        collection: Milvus collection object
        batch_size: Number of chunks per batch
        api_key: OpenAI API key
        dry_run: If True, don't actually insert into Milvus

    Returns:
        Ingestion statistics
    """
    stats = IngestStats()
    stats.start_time = time.time()

    # Prepare batches
    chunk_batch = []
    texts_batch = []

    print(f"\nIngesting normalized chunks from: {ext_dir}")
    print(f"Batch size: {batch_size}")
    if dry_run:
        print("DRY RUN MODE - No actual insertion")
    print()

    for chunk in ingest_from_normalized(ext_dir):
        stats.total_chunks += 1

        chunk_batch.append(chunk)
        texts_batch.append(chunk["text"])

        # Process batch when full
        if len(chunk_batch) >= batch_size:
            stats.batches += 1
            print(
                f"Processing batch {stats.batches} ({len(chunk_batch)} chunks)...",
                end=" ",
                flush=True,
            )

            # Generate embeddings
            embeddings = generate_embeddings_batch(texts_batch, api_key)

            valid_chunks = []
            valid_embeddings = []
            for c, emb in zip(chunk_batch, embeddings):
                if emb is not None:
                    valid_chunks.append(c)
                    valid_embeddings.append(emb)
                else:
                    stats.failed += 1

            if valid_chunks:
                if not dry_run:
                    inserted = insert_v2_batch(
                        collection, valid_chunks, valid_embeddings, stats
                    )
                    print(f"Inserted: {inserted}, Duplicates: {stats.duplicates}")
                else:
                    print(f"Would insert: {len(valid_chunks)} (DRY RUN)")
                    stats.successful += len(valid_chunks)
            else:
                print("Failed to generate embeddings for all chunks")

            # Reset batch
            chunk_batch = []
            texts_batch = []

    # Process remaining chunks
    if chunk_batch:
        stats.batches += 1
        print(
            f"Processing final batch {stats.batches} ({len(chunk_batch)} chunks)...",
            end=" ",
            flush=True,
        )

        embeddings = generate_embeddings_batch(texts_batch, api_key)

        valid_chunks = []
        valid_embeddings = []
        for c, emb in zip(chunk_batch, embeddings):
            if emb is not None:
                valid_chunks.append(c)
                valid_embeddings.append(emb)
            else:
                stats.failed += 1

        if valid_chunks:
            if not dry_run:
                inserted = insert_v2_batch(
                    collection, valid_chunks, valid_embeddings, stats
                )
                print(f"Inserted: {inserted}, Duplicates: {stats.duplicates}")
            else:
                print(f"Would insert: {len(valid_chunks)} (DRY RUN)")
                stats.successful += len(valid_chunks)
        else:
            print("Failed to generate embeddings for all chunks")

    # Flush collection to ensure data is persisted
    if not dry_run and stats.successful > 0:
        try:
            collection.flush()
            print("\nFlushed collection to disk")
        except MilvusException as e:
            print(f"\nWARNING: Failed to flush collection: {e}")

    stats.end_time = time.time()
    return stats


# ============================================================================
# Statistics and Reporting
# ============================================================================


def print_statistics(
    stats: IngestStats, collection: Optional[Collection] = None
) -> None:
    """
    Print ingestion statistics.

    Args:
        stats: Ingestion statistics
        collection: Milvus collection (for final count)
    """
    print("\n" + "=" * 60)
    print("INGESTION STATISTICS")
    print("=" * 60)
    print(f"Total chunks processed:  {stats.total_chunks}")
    print(f"Successfully ingested:   {stats.successful}")
    print(f"Failed:                  {stats.failed}")
    print(f"Duplicates skipped:      {stats.duplicates}")
    print(f"Batches processed:       {stats.batches}")
    print(f"Duration:                {stats.duration:.2f}s")
    print(f"Success rate:            {stats.success_rate:.1f}%")

    if collection:
        try:
            total_entities = collection.num_entities
            print(f"\nTotal entities in collection: {total_entities}")
        except MilvusException:
            print("\n(Could not retrieve entity count)")

    if stats.failed > 0:
        print(f"\nWARNING: {stats.failed} chunks failed to ingest")
        print("Check logs above for details")


def validate_collection(collection: Collection) -> bool:
    """
    Validate collection by running a test query.

    Args:
        collection: Milvus collection

    Returns:
        True if validation passed, False otherwise
    """
    try:
        # Get collection info (skip .loaded check - not available in all versions)
        num_entities = collection.num_entities
        print(f"\nCollection validation:")
        print(f"  - Entities: {num_entities}")
        print(f"  - Schema: {collection.schema}")
        print(f"  - Indexes: {collection.indexes}")

        return True
    except MilvusException as e:
        print(f"\nWARNING: Collection validation failed: {e}")
        return False


# ============================================================================
# CLI Interface
# ============================================================================


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest RAG-optimized chunks into Milvus vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python3 scripts/milvus_ingest.py data/rag/chunks.jsonl

  # Custom collection and Milvus host
  python3 scripts/milvus_ingest.py chunks.jsonl --collection my_papers --milvus-host milvus.example.com

  # With paper catalog for metadata
  python3 scripts/milvus_ingest.py chunks.jsonl --catalog data/metadata/paper_catalog.jsonl

  # Dry run (no actual insertion)
  python3 scripts/milvus_ingest.py chunks.jsonl --dry-run

  # Custom batch size
  python3 scripts/milvus_ingest.py chunks.jsonl --batch-size 50

Environment Variables:
  OPENAI_API_KEY    OpenAI API key for embeddings (required)
  MILVUS_HOST       Milvus server host (default: localhost)
  MILVUS_PORT       Milvus server port (default: 19530)
        """,
    )

    parser.add_argument("chunks_file", type=Path, help="Path to chunks JSONL file")

    parser.add_argument(
        "--collection",
        "-c",
        type=str,
        default=DEFAULT_COLLECTION,
        help=f"Milvus collection name (default: {DEFAULT_COLLECTION})",
    )

    parser.add_argument(
        "--milvus-host",
        type=str,
        default=os.environ.get("MILVUS_HOST", DEFAULT_MILVUS_HOST),
        help=f"Milvus server host (default: {DEFAULT_MILVUS_HOST})",
    )

    parser.add_argument(
        "--milvus-port",
        "-p",
        type=int,
        default=int(os.environ.get("MILVUS_PORT", str(DEFAULT_MILVUS_PORT))),
        help=f"Milvus server port (default: {DEFAULT_MILVUS_PORT})",
    )

    parser.add_argument(
        "--catalog",
        type=Path,
        help="Path to paper catalog JSONL file for metadata enrichment",
    )

    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of chunks per batch (default: {DEFAULT_BATCH_SIZE})",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenAI API key (or set OPENAI_API_KEY environment variable)",
    )

    parser.add_argument(
        "--index-type",
        type=str,
        default="HNSW",
        choices=["HNSW", "IVF_FLAT", "IVF_SQ8", "FLAT"],
        help="Vector index type (default: HNSW)",
    )

    parser.add_argument(
        "--metric-type",
        type=str,
        default="COSINE",
        choices=["COSINE", "L2", "IP"],
        help="Distance metric type (default: COSINE)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and prepare chunks without actual insertion",
    )

    parser.add_argument(
        "--no-load",
        action="store_true",
        help="Skip loading collection into memory after insertion",
    )

    parser.add_argument(
        "--source",
        type=str,
        choices=["rag_chunks", "normalized"],
        default="rag_chunks",
        help="Source format: 'rag_chunks' (legacy JSONL) or 'normalized' (normalized.json)",
    )

    parser.add_argument(
        "--ollama",
        action="store_true",
        help="Use Ollama local embeddings instead of OpenAI (uses nomic-embed-text)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    global USE_OLLAMA_EMBEDDINGS, EMBEDDING_DIM
    args = parse_arguments()

    # Handle Ollama embedding mode
    if args.ollama:
        USE_OLLAMA_EMBEDDINGS = True
        EMBEDDING_DIM = OLLAMA_EMBEDDING_DIM
        print(
            f"Using Ollama embeddings ({OLLAMA_EMBEDDING_MODEL}, dim={EMBEDDING_DIM})"
        )

    # Check dependencies
    if not MILVUS_AVAILABLE:
        print("ERROR: pymilvus library not installed")
        print("Install with: pip install pymilvus")
        return 1

    if not OPENAI_AVAILABLE and not USE_OLLAMA_EMBEDDINGS:
        print("ERROR: openai library not installed")
        print("Install with: pip install openai")
        return 1

    # Check OpenAI API key (skip if using Ollama)
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key and not args.dry_run and not USE_OLLAMA_EMBEDDINGS:
        print("ERROR: OpenAI API key not found")
        print("Set OPENAI_API_KEY environment variable or use --api-key")
        return 1
        return 1

    # Validate input path based on source mode
    if args.source == "normalized":
        # For normalized mode, chunks_file is actually a directory
        ext_dir = args.chunks_file
        if not ext_dir.is_dir():
            print(
                f"ERROR: For --source normalized, provide extraction directory: {ext_dir}"
            )
            return 1
        normalized_file = ext_dir / "normalized.json"
        if not normalized_file.exists():
            print(f"ERROR: normalized.json not found in: {ext_dir}")
            return 1
    else:
        # Legacy rag_chunks mode
        if not args.chunks_file.exists():
            print(f"ERROR: Chunks file not found: {args.chunks_file}")
            return 1

    # Auto-detect catalog if not specified (only for rag_chunks mode)
    catalog_path = args.catalog
    if catalog_path is None and args.source == "rag_chunks":
        default_catalog = Path("/LAB/@thesis/datalab/data/metadata/paper_catalog.jsonl")
        if default_catalog.exists():
            catalog_path = default_catalog
            print(f"Using default catalog: {default_catalog}")

    # Connect to Milvus
    if not connect_milvus(args.milvus_host, args.milvus_port):
        return 1

    try:
        # Create or load collection (use V2 schema for normalized mode)
        if args.source == "normalized":
            collection = create_v2_collection_if_not_exists(
                args.collection,
                index_type=args.index_type,
                metric_type=args.metric_type,
            )
        else:
            collection = create_collection_if_not_exists(
                args.collection,
                index_type=args.index_type,
                metric_type=args.metric_type,
            )

        if collection is None:
            print("ERROR: Failed to create/load collection")
            return 1

        # Load collection for search (optional)
        if not args.no_load and not args.dry_run:
            load_collection(collection)

        # Ingest chunks based on source mode
        if args.source == "normalized":
            stats = ingest_normalized_chunks(
                args.chunks_file,
                collection,
                batch_size=args.batch_size,
                api_key=api_key,
                dry_run=args.dry_run,
            )
        else:
            stats = ingest_chunks(
                args.chunks_file,
                collection,
                catalog_path,
                batch_size=args.batch_size,
                api_key=api_key,
                dry_run=args.dry_run,
            )

        # Print statistics
        print_statistics(stats, collection if not args.dry_run else None)

        # Validate collection
        if not args.dry_run and not args.no_load:
            validate_collection(collection)

        # Return status
        return 0 if stats.failed == 0 or stats.successful > 0 else 1

    finally:
        disconnect_milvus()


if __name__ == "__main__":
    sys.exit(main())
