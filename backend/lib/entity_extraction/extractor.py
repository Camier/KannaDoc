"""V3.1-aware extraction helpers for LAYRA.

This file focuses on:
- building V3.1 prompts (via prompt.py)
- parsing + normalizing LLM outputs into ExtractionResult (schemas.py)

It intentionally keeps API-client specifics minimal: integrate this parser
with Zhipu/MiniMax/etc. by feeding the raw model response text.

Key features
- Robust JSON extraction (handles code fences and surrounding text)
- Normalization:
  - ensures attributes/source_chunk_ids exist
  - ensures chunk_id is present in every node/edge provenance
  - drops unknown entity/relationship types in non-strict mode
  - infers INVOLVES.role when missing (best effort)
  - canonicalizes INTERACTS_WITH ordering

"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple, cast, get_args

from pydantic import ValidationError

from .prompt import build_messages_v31
from .schemas import (
    CONFIDENCE_VERIFIED_THRESHOLD,
    EntityType,
    ExtractionResult,
    RelationType,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Client protocol (optional)
# ----------------------------------------------------------------------------


class ChatClient(Protocol):
    """Minimal protocol for a chat-style LLM client.

    Your existing Zhipu/MiniMax client can adapt to this by exposing either:
    - chat(messages, **kwargs) -> str
    - complete(messages, **kwargs) -> str
    """

    def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str: ...


# ----------------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------------


class ExtractionParseError(RuntimeError):
    pass


# ----------------------------------------------------------------------------
# JSON extraction
# ----------------------------------------------------------------------------


_CODE_FENCE_PREFIXES = ("```json", "```JSON", "```")


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    for prefix in _CODE_FENCE_PREFIXES:
        if t.startswith(prefix):
            # Remove the first line (``` or ```json)
            lines = t.splitlines()
            if len(lines) >= 2:
                t = "\n".join(lines[1:])
            # Remove trailing fence if present
            if t.strip().endswith("```"):
                t = t.strip()[:-3]
            return t.strip()
    return t


def _extract_first_json_object(text: str) -> str:
    """Extract the first JSON object from text.

    This is string-aware (handles braces inside quoted strings).
    """

    s = text
    start = s.find("{")
    if start == -1:
        raise ExtractionParseError("No JSON object start '{' found in LLM response")

    in_string = False
    escape = False
    depth = 0

    for i in range(start, len(s)):
        ch = s[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        # not in string
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]

    raise ExtractionParseError("Unbalanced JSON braces in LLM response")


def _loads_json_object(text: str) -> Dict[str, Any]:
    cleaned = _strip_code_fences(text)
    json_str = _extract_first_json_object(cleaned)
    try:
        obj = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ExtractionParseError(f"Invalid JSON from LLM: {e}") from e

    if not isinstance(obj, dict):
        raise ExtractionParseError("Top-level JSON must be an object with keys 'entities' and 'relationships'")
    return cast(Dict[str, Any], obj)


# ----------------------------------------------------------------------------
# Normalization helpers
# ----------------------------------------------------------------------------


_ALLOWED_ENTITY_TYPES = set(get_args(EntityType))
_ALLOWED_RELATION_TYPES = set(get_args(RelationType))


_ROLE_BY_TARGET_TYPE: Dict[str, str] = {
    "Taxon": "taxon",
    "PlantPart": "plant_part",
    "Preparation": "preparation",
    "RawMaterial": "raw_material",
    "TraditionalUse": "traditional_use",
}


def _ensure_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _ensure_dict(x: Any) -> Dict[str, Any]:
    if isinstance(x, dict):
        return x
    return {}


def _coerce_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        # clamp into [0,1] if out of range but numeric
        v = float(x)
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v
    if isinstance(x, str):
        try:
            v = float(x.strip())
            if v < 0.0:
                return 0.0
            if v > 1.0:
                return 1.0
            return v
        except Exception:
            return None
    return None


def normalize_extraction_dict(raw: Dict[str, Any], *, chunk_id: str, strict: bool = False) -> Dict[str, Any]:
    """Normalize an LLM-produced dict into a shape compatible with ExtractionResult.

    - Ensures lists/dicts exist
    - Filters/drops unknown types if strict=False
    - Ensures chunk_id appears in all source_chunk_ids
    - Ensures INVOLVES.role exists (best-effort inference)
    - Drops relationships that reference unknown/missing entities
    """

    entities_in = raw.get("entities", [])
    rels_in = raw.get("relationships", [])

    if not isinstance(entities_in, list):
        entities_in = []
    if not isinstance(rels_in, list):
        rels_in = []

    # First pass: normalize + filter entities
    kept_entities: List[Dict[str, Any]] = []
    entity_type_by_id: Dict[str, str] = {}

    for ent in entities_in:
        if not isinstance(ent, dict):
            if strict:
                raise ExtractionParseError("Entity must be an object")
            continue

        etype = ent.get("type")
        if etype not in _ALLOWED_ENTITY_TYPES:
            if strict:
                raise ExtractionParseError(f"Unknown entity type: {etype}")
            logger.warning("Dropping entity with unknown type: %s", etype)
            continue

        eid = ent.get("id")
        name = ent.get("name")
        if not isinstance(eid, str) or not eid:
            if strict:
                raise ExtractionParseError("Entity missing valid 'id'")
            continue
        if not isinstance(name, str) or not name:
            if strict:
                raise ExtractionParseError("Entity missing valid 'name'")
            continue

        ent_norm: Dict[str, Any] = {
            "id": eid,
            "type": etype,
            "name": name,
            "attributes": _ensure_dict(ent.get("attributes")),
            "source_chunk_ids": _ensure_list(ent.get("source_chunk_ids")),
            "confidence": _coerce_float(ent.get("confidence")),
            "evidence": ent.get("evidence"),
        }

        # Ensure chunk provenance
        scids = [c for c in ent_norm["source_chunk_ids"] if isinstance(c, str) and c]
        if chunk_id not in scids:
            scids.append(chunk_id)
        ent_norm["source_chunk_ids"] = scids

        # Let schemas.py compute verified; ignore if model sets it.
        if "verified" in ent:
            ent_norm["verified"] = bool(ent.get("verified"))

        kept_entities.append(ent_norm)
        entity_type_by_id[eid] = cast(str, etype)

    kept_entity_ids = set(entity_type_by_id.keys())

    # Second pass: normalize + filter relationships
    kept_rels: List[Dict[str, Any]] = []

    for rel in rels_in:
        if not isinstance(rel, dict):
            if strict:
                raise ExtractionParseError("Relationship must be an object")
            continue

        rtype = rel.get("type")
        if rtype not in _ALLOWED_RELATION_TYPES:
            if strict:
                raise ExtractionParseError(f"Unknown relationship type: {rtype}")
            logger.warning("Dropping relationship with unknown type: %s", rtype)
            continue

        rid = rel.get("id")
        sid = rel.get("source_entity_id")
        tid = rel.get("target_entity_id")

        if not isinstance(rid, str) or not rid:
            if strict:
                raise ExtractionParseError("Relationship missing valid 'id'")
            continue
        if not isinstance(sid, str) or not sid:
            if strict:
                raise ExtractionParseError("Relationship missing valid 'source_entity_id'")
            continue
        if not isinstance(tid, str) or not tid:
            if strict:
                raise ExtractionParseError("Relationship missing valid 'target_entity_id'")
            continue

        # Drop edges referencing missing entities
        if sid not in kept_entity_ids or tid not in kept_entity_ids:
            if strict:
                raise ExtractionParseError(f"Relationship {rid} references missing entities")
            continue

        attrs = _ensure_dict(rel.get("attributes"))

        # Ensure role on INVOLVES
        if rtype == "INVOLVES":
            role = attrs.get("role")
            if not isinstance(role, str) or not role:
                # infer by target entity type
                tgt_type = entity_type_by_id.get(tid)
                inferred = _ROLE_BY_TARGET_TYPE.get(str(tgt_type))
                if inferred is not None:
                    attrs["role"] = inferred
                elif strict:
                    raise ExtractionParseError("INVOLVES relationship missing attributes.role")

        # Canonicalize INTERACTS_WITH ordering
        if rtype == "INTERACTS_WITH":
            if sid == tid:
                if strict:
                    raise ExtractionParseError("INTERACTS_WITH self-loop is not allowed")
                continue
            a, b = (sid, tid) if sid <= tid else (tid, sid)
            sid, tid = a, b
            attrs.setdefault("bidirectional", True)

        rel_norm: Dict[str, Any] = {
            "id": rid,
            "type": rtype,
            "source_entity_id": sid,
            "target_entity_id": tid,
            "attributes": attrs,
            "source_chunk_ids": _ensure_list(rel.get("source_chunk_ids")),
            "confidence": _coerce_float(rel.get("confidence")),
            "evidence": rel.get("evidence"),
            "supporting_study_ids": _ensure_list(rel.get("supporting_study_ids")),
        }

        # Ensure chunk provenance
        scids = [c for c in rel_norm["source_chunk_ids"] if isinstance(c, str) and c]
        if chunk_id not in scids:
            scids.append(chunk_id)
        rel_norm["source_chunk_ids"] = scids

        # Normalize supporting study ids to strings only
        rel_norm["supporting_study_ids"] = [
            s for s in rel_norm["supporting_study_ids"] if isinstance(s, str) and s
        ]

        if "verified" in rel:
            rel_norm["verified"] = bool(rel.get("verified"))

        kept_rels.append(rel_norm)

    return {
        "entities": kept_entities,
        "relationships": kept_rels,
    }


def parse_extraction_result(
    llm_response_text: str,
    *,
    chunk_id: str,
    strict: bool = False,
) -> ExtractionResult:
    """Parse an LLM response into an ExtractionResult.

    Parameters
    - llm_response_text: raw text from the model
    - chunk_id: the chunk id used for provenance injection
    - strict: if True, raise on unknown types / malformed objects;
              if False, best-effort salvage by dropping invalid items.
    """

    raw_obj = _loads_json_object(llm_response_text)
    norm = normalize_extraction_dict(raw_obj, chunk_id=chunk_id, strict=strict)
    try:
        return ExtractionResult.model_validate(norm)
    except ValidationError as e:
        # In strict=False mode, surface a concise error but include the underlying details.
        raise ExtractionParseError(f"ExtractionResult validation failed: {e}") from e


# ----------------------------------------------------------------------------
# Optional end-to-end wrapper
# ----------------------------------------------------------------------------


@dataclass
class V31Extractor:
    """Thin wrapper around a chat client to produce ExtractionResult.

    This is intentionally minimal: integrate into your existing Zhipu/MiniMax
    code by adapting your client to `chat(messages, **kwargs) -> str`.
    """

    client: ChatClient
    model: Optional[str] = None
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    strict_parse: bool = False

    def extract(self, *, doc_id: str, chunk_id: str, text: str) -> ExtractionResult:
        messages = build_messages_v31(doc_id=doc_id, chunk_id=chunk_id, text=text)

        # Prefer `.chat`, but support `.complete` if present.
        if hasattr(self.client, "chat"):
            content = self.client.chat(
                messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        elif hasattr(self.client, "complete"):
            content = getattr(self.client, "complete")(
                messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        else:
            raise RuntimeError("LLM client must implement chat(...) or complete(...)")

        return parse_extraction_result(content, chunk_id=chunk_id, strict=self.strict_parse)


__all__ = [
    "ExtractionParseError",
    "normalize_extraction_dict",
    "parse_extraction_result",
    "V31Extractor",
]
