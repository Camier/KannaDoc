"""MinimaxM2.1 entity extractor for ethnopharmacology documents."""

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.entity_extraction.prompt import build_prompt
from lib.entity_extraction.schemas import (
    Entity,
    ExtractionResultV2,
    Relationship,
)

logger = logging.getLogger(__name__)

# Optimized system prompt following MiniMax best practices:
# - Be clear and specific with instructions
# - Explain intent ("why") to improve performance
# - Focus on single task (entity extraction only)
SYSTEM_PROMPT = """You are an expert ethnopharmacology knowledge extractor for building a biomedical knowledge graph.

Your task is to extract structured entities and relationships from scientific text about medicinal plants.

CRITICAL REQUIREMENTS:
1. Return ONLY valid JSON - no markdown, no explanation, no preamble
2. Extract ALL relevant entities mentioned in the text
3. Create relationships ONLY when the text explicitly supports them
4. Use the exact entity types and relationship types specified in the user prompt
5. Generate unique IDs: ent_001, ent_002, ... for entities; rel_001, rel_002, ... for relationships
6. Do NOT include <think> tags or any hidden reasoning

Your output will be parsed programmatically, so JSON validity is essential."""


def _load_api_key() -> str:
    """Load API key from environment variable or legacy file."""
    # Try environment variable first (preferred)
    key = os.getenv("MINIMAX_API_KEY")
    if key:
        return key.strip()
    # Fallback to legacy file for backwards compatibility
    key_file = Path("data/.minimax_api_key")
    if key_file.exists():
        return key_file.read_text().strip()
    raise ValueError(
        "MINIMAX_API_KEY not found. Set environment variable MINIMAX_API_KEY in .env"
    )


class MinimaxExtractor:
    """Entity extractor using MiniMax-M2.1 API.

    Optimized based on MiniMax official documentation:
    - temperature=1.0 (required for M2.1)
    - top_p=0.95 (recommended for reasoning models)
    - max_completion_tokens=4096 (prevent truncation)
    - Uses 'lightning' variant for 67% faster processing when available
    """

    # Model variants
    MODEL_STANDARD = "MiniMax-M2.1"  # ~60 tps, best reasoning
    MODEL_LIGHTNING = "MiniMax-M2.1-lightning"  # ~100 tps, faster

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "MiniMax-M2.1",
        use_lightning: bool = False,
    ):
        import openai

        self.api_key = api_key or _load_api_key()
        self.model = self.MODEL_LIGHTNING if use_lightning else model
        self.client = openai.OpenAI(
            base_url="https://api.minimax.io/v1",
            api_key=self.api_key,
            timeout=120.0,  # Increased for longer extractions
        )

    def extract_chunk(
        self,
        text: str,
        doc_id: str = "",
        chunk_id: str = "",
    ) -> ExtractionResultV2:
        if not text or len(text.strip()) < 20:
            return self._empty_result(doc_id)
        prompt = build_prompt(text)
        delays = [1, 2, 4]
        last_error = None
        for attempt, delay in enumerate(delays):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT,
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=1.0,  # Required: range (0.0, 1.0]
                    top_p=0.95,  # Recommended for M2 reasoning models
                    max_completion_tokens=4096,  # Prevent truncation on complex extractions
                    extra_body={"reasoning_split": True},
                )
                content = (response.choices[0].message.content or "").strip()
                return self._parse_response(content, doc_id, chunk_id)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if "rate" in error_str or "429" in error_str or "timeout" in error_str:
                    if attempt < len(delays) - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                        )
                        time.sleep(delay)
                        continue
                logger.warning(f"Extraction failed for chunk {chunk_id}: {e}")
                break
        logger.warning(f"All retries exhausted for chunk {chunk_id}: {last_error}")
        return self._empty_result(doc_id)

    def extract_document(
        self,
        chunks: List[Dict[str, Any]],
        doc_id: str,
        max_workers: int = 4,
    ) -> ExtractionResultV2:
        all_entities: List[Entity] = []
        all_relationships: List[Relationship] = []
        chunks_to_process = []
        for i, chunk in enumerate(chunks):
            text = chunk.get("text") or chunk.get("content", "")
            if not text or len(text.strip()) < 50:
                continue
            chunk_id = chunk.get("id") or chunk.get("chunk_id") or f"chunk_{i:04d}"
            chunks_to_process.append({"text": text, "chunk_id": chunk_id})
        if not chunks_to_process:
            return self._empty_result(doc_id)
        logger.info(f"Processing {len(chunks_to_process)} chunks for {doc_id}")

        def process_chunk(item: Dict[str, str]) -> ExtractionResultV2:
            return self.extract_chunk(item["text"], doc_id, item["chunk_id"])

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_chunk, item): item for item in chunks_to_process
            }
            completed = 0
            for future in as_completed(futures):
                completed += 1
                try:
                    result = future.result()
                    chunk_id = futures[future]["chunk_id"]
                    for entity in result.entities:
                        if chunk_id not in entity.source_chunk_ids:
                            entity.source_chunk_ids.append(chunk_id)
                    all_entities.extend(result.entities)
                    all_relationships.extend(result.relationships)
                    if completed % 10 == 0:
                        logger.info(
                            f"  Processed {completed}/{len(chunks_to_process)} chunks"
                        )
                except Exception as e:
                    logger.warning(f"Chunk processing failed: {e}")
        logger.info(
            f"Extracted {len(all_entities)} entities, {len(all_relationships)} relationships"
        )
        return ExtractionResultV2(
            doc_id=doc_id,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor=f"minimax:{self.model}",
            entities=all_entities,
            relationships=all_relationships,
            metadata={"chunks_processed": len(chunks_to_process)},
        )

    def _parse_response(
        self, content: str, doc_id: str, chunk_id: str
    ) -> ExtractionResultV2:
        parsed = self._extract_json(content)
        if not parsed:
            logger.warning(f"Failed to parse JSON for chunk {chunk_id}")
            return self._empty_result(doc_id)
        entities = []
        for ent_data in parsed.get("entities", []):
            try:
                entities.append(
                    Entity(
                        id=ent_data.get("id", f"ent_{len(entities):03d}"),
                        type=ent_data.get("type", "Unknown"),
                        name=ent_data.get("name", ""),
                        attributes=ent_data.get("attributes", {}),
                        source_chunk_ids=[chunk_id] if chunk_id else [],
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse entity: {e}")
        relationships = []
        for rel_data in parsed.get("relationships", []):
            try:
                relationships.append(
                    Relationship(
                        id=rel_data.get("id", f"rel_{len(relationships):03d}"),
                        type=rel_data.get("type", "SUGGESTS"),
                        source_entity_id=rel_data.get("source_entity_id", ""),
                        target_entity_id=rel_data.get("target_entity_id", ""),
                        attributes=rel_data.get("attributes", {}),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse relationship: {e}")
        return ExtractionResultV2(
            doc_id=doc_id,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor=f"minimax:{self.model}",
            entities=entities,
            relationships=relationships,
        )

    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        try:
            result = json.loads(content)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        obj_match = re.search(r"\{[\s\S]*\}", content)
        if obj_match:
            try:
                result = json.loads(obj_match.group(0))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        return None

    def _empty_result(self, doc_id: str) -> ExtractionResultV2:
        return ExtractionResultV2(
            doc_id=doc_id,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor=f"minimax:{self.model}",
            entities=[],
            relationships=[],
        )


class ZhipuExtractor:
    """Entity extractor using Zhipu GLM-4 via Z.ai API.
    
    Uses JSON Schema mode for reliable structured output.
    Models: glm-4-plus (flagship), glm-4-flash (fast), glm-4-air (cheap)
    
    Advantages over MiniMax:
    - Native JSON Schema mode eliminates parse failures
    - 80% cost savings with glm-4-air ($0.15 flat rate)
    - Uses relationship type normalization for robust output
    """

    MODEL_PLUS = "glm-4.7"
    MODEL_FLASH = "glm-4.7-flash"  
    MODEL_AIR = "glm-4.5-air"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "glm-4.7-flash",
        base_url: str = "https://api.z.ai/api/coding/paas/v4",
    ):
        import openai
        from lib.entity_extraction.schemas import normalize_relationship_type
        
        self.api_key = api_key or os.getenv("ZAI_API_KEY") or os.getenv("ZHIPU_API_KEY")
        if not self.api_key:
            raise ValueError("ZAI_API_KEY or ZHIPU_API_KEY not found in environment")
        
        self.model = model
        self.normalize_rel = normalize_relationship_type
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key=self.api_key,
            timeout=120.0,
        )

    def extract_chunk(
        self, 
        text: str, 
        doc_id: str = "", 
        chunk_id: str = ""
    ) -> ExtractionResultV2:
        """Extract entities and relationships from a single text chunk."""
        if not text or len(text.strip()) < 20:
            return self._empty_result(doc_id)
        
        prompt = build_prompt(text)
        
        # JSON Schema for structured output - ensures valid JSON every time
        json_schema = {
            "name": "extraction_result",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "type": {"type": "string"},
                                "name": {"type": "string"},
                                "attributes": {"type": "object"}
                            },
                            "required": ["id", "type", "name"],
                            "additionalProperties": False
                        }
                    },
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "type": {"type": "string"},
                                "source_entity_id": {"type": "string"},
                                "target_entity_id": {"type": "string"},
                                "attributes": {"type": "object"}
                            },
                            "required": ["id", "type", "source_entity_id", "target_entity_id"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["entities", "relationships"],
                "additionalProperties": False
            }
        }
        
        delays = [1, 2, 4]
        last_error = None
        
        for attempt, delay in enumerate(delays):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=4096,
                    response_format={
                        "type": "json_schema",
                        "json_schema": json_schema,
                    },
                )
                content = (response.choices[0].message.content or "").strip()
                return self._parse_response(content, doc_id, chunk_id)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if "rate" in error_str or "429" in error_str or "timeout" in error_str:
                    if attempt < len(delays) - 1:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                        time.sleep(delay)
                        continue
                logger.warning(f"Extraction failed for chunk {chunk_id}: {e}")
                break
        
        logger.warning(f"All retries exhausted for chunk {chunk_id}: {last_error}")
        return self._empty_result(doc_id)

    def extract_document(
        self,
        chunks: List[Dict[str, Any]],
        doc_id: str,
        max_workers: int = 4,
    ) -> ExtractionResultV2:
        """Extract entities from all chunks in a document."""
        all_entities: List[Entity] = []
        all_relationships: List[Relationship] = []
        chunks_to_process = []
        
        for i, chunk in enumerate(chunks):
            text = chunk.get("text") or chunk.get("content", "")
            if not text or len(text.strip()) < 50:
                continue
            chunk_id = chunk.get("id") or chunk.get("chunk_id") or f"chunk_{i:04d}"
            chunks_to_process.append({"text": text, "chunk_id": chunk_id})
        
        if not chunks_to_process:
            return self._empty_result(doc_id)
        
        logger.info(f"Processing {len(chunks_to_process)} chunks for {doc_id} with Zhipu")

        def process_chunk(item: Dict[str, str]) -> ExtractionResultV2:
            return self.extract_chunk(item["text"], doc_id, item["chunk_id"])

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_chunk, item): item for item in chunks_to_process
            }
            completed = 0
            for future in as_completed(futures):
                completed += 1
                try:
                    result = future.result()
                    chunk_id = futures[future]["chunk_id"]
                    for entity in result.entities:
                        if chunk_id not in entity.source_chunk_ids:
                            entity.source_chunk_ids.append(chunk_id)
                    all_entities.extend(result.entities)
                    all_relationships.extend(result.relationships)
                    if completed % 10 == 0:
                        logger.info(
                            f"  Processed {completed}/{len(chunks_to_process)} chunks"
                        )
                except Exception as e:
                    logger.warning(f"Chunk processing failed: {e}")
        
        logger.info(
            f"Extracted {len(all_entities)} entities, {len(all_relationships)} relationships"
        )
        return ExtractionResultV2(
            doc_id=doc_id,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor=f"zhipu:{self.model}",
            entities=all_entities,
            relationships=all_relationships,
            metadata={"chunks_processed": len(chunks_to_process)},
        )

    def _parse_response(
        self, content: str, doc_id: str, chunk_id: str
    ) -> ExtractionResultV2:
        """Parse JSON response and normalize relationship types."""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = self._extract_json(content)
            if not parsed:
                logger.warning(f"Failed to parse JSON for chunk {chunk_id}")
                return self._empty_result(doc_id)
        
        entities = []
        for ent_data in parsed.get("entities", []):
            try:
                entities.append(Entity(
                    id=ent_data.get("id", f"ent_{len(entities):03d}"),
                    type=ent_data.get("type", "Unknown"),
                    name=ent_data.get("name", ""),
                    attributes=ent_data.get("attributes", {}),
                    source_chunk_ids=[chunk_id] if chunk_id else [],
                ))
            except Exception as e:
                logger.warning(f"Failed to parse entity: {e}")
        
        relationships = []
        for rel_data in parsed.get("relationships", []):
            try:
                # NORMALIZE relationship type using the function from schemas.py
                raw_type = rel_data.get("type", "SUGGESTS")
                normalized_type = self.normalize_rel(raw_type)
                
                relationships.append(Relationship(
                    id=rel_data.get("id", f"rel_{len(relationships):03d}"),
                    type=normalized_type,  # Use normalized type
                    source_entity_id=rel_data.get("source_entity_id", ""),
                    target_entity_id=rel_data.get("target_entity_id", ""),
                    attributes=rel_data.get("attributes", {}),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse relationship: {e}")
        
        return ExtractionResultV2(
            doc_id=doc_id,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor=f"zhipu:{self.model}",
            entities=entities,
            relationships=relationships,
        )

    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Fallback JSON extraction for non-schema responses."""
        content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        try:
            result = json.loads(content)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        obj_match = re.search(r"\{[\s\S]*\}", content)
        if obj_match:
            try:
                result = json.loads(obj_match.group(0))
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        return None

    def _empty_result(self, doc_id: str) -> ExtractionResultV2:
        """Return an empty extraction result."""
        return ExtractionResultV2(
            doc_id=doc_id,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extractor=f"zhipu:{self.model}",
            entities=[],
            relationships=[],
        )
