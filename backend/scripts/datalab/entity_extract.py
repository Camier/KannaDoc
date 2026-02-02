#!/usr/bin/env python3
"""
Entity Extraction Script for DataLab

Extracts named entities from RAG chunks using GPT-4o-mini.
Outputs per-document entities.json with chunk_entities array format.

Entity Types:
  - Compound: Chemical compounds, alkaloids, molecules
  - Plant: Plant species (scientific and common names)
  - Effect: Pharmacological effects (anti-inflammatory, anxiolytic, etc.)
  - Disease: Medical conditions or diseases
  - Dosage: Dosage information with amounts and units

Usage:
    # Test mode with sample text
    python3 scripts/entity_extract.py --test "Curcumin from Curcuma longa shows anti-inflammatory effects"

    # Process extraction directory
    python3 scripts/entity_extract.py data/PROD_EXTRACTION_V2/<extraction_dir>/
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional
import warnings

warnings.warn(
    "entity_extract.py is deprecated. Use extract_entities_v2.py instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)

# Entity types for extraction
ENTITY_TYPES = ["Compound", "Plant", "Effect", "Disease", "Dosage"]

# Prompt template for entity extraction
ENTITY_EXTRACTION_PROMPT = """Extract entities from this scientific text about ethnopharmacology.

Text: {text}

Extract the following entity types:
- Compound: Chemical compounds, alkaloids, molecules
- Plant: Plant species (scientific and common names)
- Effect: Pharmacological effects (anti-inflammatory, anxiolytic, etc.)
- Disease: Medical conditions or diseases
- Dosage: Dosage information with amounts and units

Return JSON array of entities:
[{{"type": "Compound", "name": "...", "context": "..."}}, ...]

Rules:
- Extract ALL relevant entities from the text
- For context, include a brief phrase showing where the entity appears
- Normalize plant names to scientific format when possible
- Be precise with compound names (full chemical names)
- Return empty array [] if no entities found
- Return ONLY the JSON array, no additional text"""


class HTMLTextExtractor(HTMLParser):
    """HTML parser that extracts plain text."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {"script", "style", "nav", "footer", "header"}
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self) -> str:
        text = " ".join(self.text_parts)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def html_to_text(html: str) -> str:
    """Convert HTML to plain text."""
    if not html:
        return ""
    decoded = unescape(html)
    parser = HTMLTextExtractor()
    try:
        parser.feed(decoded)
        return parser.get_text()
    except Exception:
        # Fallback: strip tags with regex
        clean = re.sub(r"<[^>]+>", " ", decoded)
        return re.sub(r"\s+", " ", clean).strip()


def make_entity_id(entity_type: str, name: str) -> str:
    """
    Generate canonical entity ID.

    Args:
        entity_type: Entity type (Compound, Plant, etc.)
        name: Entity name

    Returns:
        Normalized entity ID string
    """
    normalized = name.lower().replace(" ", "_").replace("-", "_")[:50]
    # Remove any non-alphanumeric chars except underscore
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    return f"{entity_type.lower()}_{normalized}"


def compute_chunk_id(content: str) -> str:
    """Compute SHA256 hash for chunk identification."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_ENTITY_MODEL", "qwen3-vl:8b")


class OllamaEntityExtractor:
    """Entity extractor using local Ollama model."""

    def __init__(self, model: Optional[str] = None):
        """Initialize Ollama extractor."""
        import requests

        self.model = model or OLLAMA_MODEL
        self._session = requests.Session()
        self._last_request_time = 0
        self._min_request_interval = 0.1

    def _rate_limit(self):
        """Apply rate limiting between API calls."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text using Ollama."""
        if not text or len(text.strip()) < 20:
            return []

        self._rate_limit()

        max_chars = 4000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)
        system_prompt = "You are an expert in ethnopharmacology. Extract entities precisely and return valid JSON only."

        try:
            response = self._session.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\n{prompt}",
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 2048},
                },
                timeout=60,
            )
            response.raise_for_status()
            result = response.json().get("response", "")

            # Parse JSON from response
            json_match = re.search(r"\[.*?\]", result, re.DOTALL)
            if json_match:
                entities = json.loads(json_match.group())
                for entity in entities:
                    if "entity_id" not in entity:
                        entity["entity_id"] = make_entity_id(
                            entity.get("type", "Unknown"), entity.get("name", "unknown")
                        )
                return entities
            return []
        except Exception as e:
            logger.warning(f"Ollama extraction failed: {e}")
            return []


class EntityExtractor:
    """LLM-based entity extractor using GPT-4o-mini."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize extractor.

        Args:
            api_key: OpenAI API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests

        # Import openai lazily
        try:
            import openai

            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def _rate_limit(self):
        """Apply rate limiting between API calls."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text using GPT-4o-mini.

        Args:
            text: Text to extract entities from

        Returns:
            List of entity dictionaries with type, name, context, entity_id
        """
        if not text or len(text.strip()) < 20:
            return []

        # Rate limit
        self._rate_limit()

        # Truncate very long text
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in ethnopharmacology. Extract entities precisely and return valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
            )

            content = (response.choices[0].message.content or "").strip()

            # Parse JSON response
            entities = self._parse_json_response(content)

            # Add entity_id to each entity
            for entity in entities:
                if "type" in entity and "name" in entity:
                    entity["entity_id"] = make_entity_id(entity["type"], entity["name"])

            return entities

        except Exception as e:
            logger.warning(f"[ERROR] Entity extraction failed: {e}")
            return []

    def _parse_json_response(self, content: str) -> List[Dict[str, Any]]:
        """Parse JSON from LLM response, handling common issues."""
        # Try direct parse first
        try:
            result = json.loads(content)
            if isinstance(result, list):
                return result
            return []
        except json.JSONDecodeError:
            pass

        # Try to extract JSON array from response
        patterns = [
            r"\[[\s\S]*\]",  # Match [...] anywhere
            r"```json\s*([\s\S]*?)```",  # Match ```json ... ```
            r"```\s*([\s\S]*?)```",  # Match ``` ... ```
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    json_str = match.group(1) if match.lastindex else match.group(0)
                    result = json.loads(json_str)
                    if isinstance(result, list):
                        return result
                except (json.JSONDecodeError, IndexError):
                    continue

        return []


def load_chunks(extraction_dir: Path) -> List[Dict[str, Any]]:
    """
    Load chunks from extraction directory.

    Args:
        extraction_dir: Path to extraction directory

    Returns:
        List of chunk dictionaries
    """
    chunks_file = extraction_dir / "rag" / "chunks.jsonl"

    if not chunks_file.exists():
        # Try normalized.json as fallback
        normalized_file = extraction_dir / "normalized.json"
        if normalized_file.exists():
            with open(normalized_file) as f:
                data = json.load(f)
                return data.get("chunks", [])
        raise FileNotFoundError(f"No chunks found in {extraction_dir}")

    chunks = []
    with open(chunks_file) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return chunks


def extract_doc_id(extraction_dir: Path) -> str:
    """Extract document ID from extraction directory name."""
    # Format: YYYYMMDD_HHMMSS_UUID_NAME
    name = extraction_dir.name
    parts = name.split("_")
    if len(parts) >= 3:
        return parts[2]  # UUID portion
    return compute_chunk_id(name)


def process_extraction_dir(extraction_dir: Path, extractor: Any) -> Dict[str, Any]:
    """
    Process an extraction directory and extract entities from all chunks.

    Args:
        extraction_dir: Path to extraction directory
        extractor: EntityExtractor instance

    Returns:
        Document entities dictionary
    """
    logger.info(f"[INFO] Processing: {extraction_dir.name}")

    # Load chunks
    chunks = load_chunks(extraction_dir)
    logger.info(f"[INFO] Loaded {len(chunks)} chunks")

    # Extract doc_id
    doc_id = extract_doc_id(extraction_dir)

    # Process each chunk
    chunk_entities = []
    entity_counts = {t: 0 for t in ENTITY_TYPES}
    total_entities = 0

    for i, chunk in enumerate(chunks):
        # Get text content
        html_content = chunk.get("html", "")
        text = html_to_text(html_content)

        # Skip empty or very short chunks
        if len(text) < 50:
            continue

        # Generate chunk ID
        chunk_id = chunk.get("id") or compute_chunk_id(text)
        if isinstance(chunk_id, str) and chunk_id.startswith("/"):
            # Convert block ID to hash
            chunk_id = compute_chunk_id(chunk_id + text)

        # Extract entities
        entities = extractor.extract_entities(text)

        if entities:
            chunk_entities.append({"chunk_id": chunk_id, "entities": entities})

            for entity in entities:
                entity_type = entity.get("type", "")
                if entity_type in entity_counts:
                    entity_counts[entity_type] += 1
                total_entities += 1

        # Progress logging
        if (i + 1) % 10 == 0:
            logger.info(
                f"[INFO] Processed {i + 1}/{len(chunks)} chunks, {total_entities} entities found"
            )

    # Build result
    result = {
        "doc_id": doc_id,
        "extraction_date": datetime.now(timezone.utc).isoformat(),
        "chunk_entities": chunk_entities,
        "entity_summary": {
            "total_entities": total_entities,
            "by_type": {k: v for k, v in entity_counts.items() if v > 0},
        },
    }

    logger.info(
        f"[OK] Extracted {total_entities} entities from {len(chunk_entities)} chunks"
    )

    return result


def save_entities(entities: Dict[str, Any], output_path: Path):
    """Save entities to JSON file using atomic write."""
    tmp_path = output_path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(entities, f, indent=2)
    os.replace(tmp_path, output_path)
    logger.info(f"[OK] Saved: {output_path}")


def test_mode(text: str, extractor: Any):
    """
    Run test extraction on sample text.

    Args:
        text: Sample text to test
        extractor: EntityExtractor instance
    """
    logger.info(f"[INFO] Test mode - extracting from: {text[:80]}...")

    entities = extractor.extract_entities(text)

    result = {
        "test_input": text,
        "extraction_date": datetime.now(timezone.utc).isoformat(),
        "entities": entities,
        "entity_count": len(entities),
    }

    print(json.dumps(result, indent=2))

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract entities from RAG chunks using GPT-4o-mini"
    )
    parser.add_argument(
        "extraction_dir", nargs="?", help="Path to extraction directory"
    )
    parser.add_argument(
        "--test", type=str, help="Test mode: extract entities from provided text"
    )
    parser.add_argument(
        "--output", type=str, help="Custom output path for entities.json"
    )
    parser.add_argument(
        "--ollama", action="store_true", help="Use Ollama local model instead of OpenAI"
    )

    args = parser.parse_args()

    # Initialize extractor
    try:
        if args.ollama:
            logger.info(f"Using Ollama extractor with model {OLLAMA_MODEL}")
            extractor = OllamaEntityExtractor()
        else:
            extractor = EntityExtractor()
    except ValueError as e:
        logger.error(f"[ERROR] {e}")
        sys.exit(1)
    except ImportError as e:
        logger.error(f"[ERROR] {e}")
        sys.exit(1)

    # Test mode
    if args.test:
        test_mode(args.test, extractor)
        return

    # Directory mode
    if not args.extraction_dir:
        parser.error("extraction_dir is required when not using --test")

    extraction_dir = Path(args.extraction_dir)
    if not extraction_dir.exists():
        logger.error(f"[ERROR] Directory not found: {extraction_dir}")
        sys.exit(1)

    # Process directory
    entities = process_extraction_dir(extraction_dir, extractor)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = extraction_dir / "entities.json"

    # Save results
    save_entities(entities, output_path)


if __name__ == "__main__":
    main()
