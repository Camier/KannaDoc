"""Evidence gating for extraction schema fields.

RULE: No field reaches Neo4j/Milvus without at least one resolved citation.

Validation:
1. Field has *_citations array (non-empty)
2. Citations resolve to blocks in block_index
3. For identifiers: block must be on page <= 1 OR not in References section
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .schemas.normalized_document import BlockIndexEntry, Extraction


REFERENCES_PATTERNS = [
    r"\breferences?\b",
    r"\bbibliograph",
    r"\bliterature\s+cited\b",
    r"\bworks?\s+cited\b",
    r"\bcitations?\b",
]


def is_references_heading(text: str) -> bool:
    """Check if heading text indicates a References section."""
    if not text:
        return False
    text_lower = text.lower().strip()
    return any(re.search(pat, text_lower) for pat in REFERENCES_PATTERNS)


def get_section_headers(
    block_id: str,
    block_index: Dict[str, BlockIndexEntry],
) -> List[str]:
    """Get all section headers above a block by walking parent chain.

    Returns list of header texts from the block's ancestors.
    """
    headers: List[str] = []
    current_id = block_id

    visited: Set[str] = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        entry = block_index.get(current_id)
        if not entry:
            break

        if entry.block_type and "header" in entry.block_type.lower():
            header_text = entry.text or entry.html or ""
            if header_text:
                clean_text = re.sub(r"<[^>]+>", "", header_text).strip()
                if clean_text:
                    headers.append(clean_text)

        current_id = entry.parent_block_id

    return headers


def is_in_references_section(
    block_id: str,
    block_index: Dict[str, BlockIndexEntry],
) -> bool:
    """Check if a block is within a References/Bibliography section.

    Walks up the section hierarchy to find parent headings.
    """
    headers = get_section_headers(block_id, block_index)
    return any(is_references_heading(h) for h in headers)


def validate_identifier_citation(
    block_id: str,
    block_index: Dict[str, BlockIndexEntry],
) -> Tuple[bool, Optional[str]]:
    """Validate an identifier citation is from valid location.

    Identifiers must come from:
    - Pages 0-1 (title/header area), OR
    - Any page NOT in References section

    Returns: (is_valid, rejection_reason)
    """
    entry = block_index.get(block_id)
    if not entry:
        return False, f"block_id not found: {block_id}"

    page_index = entry.page_index

    if page_index is not None and page_index <= 1:
        return True, None

    if is_in_references_section(block_id, block_index):
        return False, f"block in References section: {block_id}"

    return True, None


def gate_extraction(
    extraction: Extraction,
    block_index: Dict[str, BlockIndexEntry],
    strict_fields: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Gate extraction data, rejecting fields without valid citations.

    Args:
        extraction: Extraction object with data, citations, anchors
        block_index: Dict mapping block_id -> BlockIndexEntry
        strict_fields: Fields requiring stricter validation (e.g. identifiers)
                      Default: {"identifiers"}

    Returns:
        Dict with:
          - gated_data: Only fields that passed validation
          - rejected_fields: Dict of field -> rejection reasons
          - validation_report: Summary stats
    """
    if strict_fields is None:
        strict_fields = {"identifiers"}

    gated_data: Dict[str, Any] = {}
    rejected_fields: Dict[str, List[str]] = {}
    stats = {
        "total_fields": 0,
        "passed": 0,
        "rejected_no_citations": 0,
        "rejected_unresolved": 0,
        "rejected_references_section": 0,
    }

    for field, value in extraction.data.items():
        stats["total_fields"] += 1

        if value is None or (isinstance(value, (list, dict, str)) and not value):
            gated_data[field] = value
            stats["passed"] += 1
            continue

        citations = extraction.citations.get(field, [])

        if not citations:
            rejected_fields[field] = ["no citations provided"]
            stats["rejected_no_citations"] += 1
            continue

        resolved_count = 0
        unresolved: List[str] = []
        references_section: List[str] = []

        for block_id in citations:
            entry = block_index.get(block_id)
            if not entry:
                unresolved.append(block_id)
                continue

            if field in strict_fields:
                is_valid, reason = validate_identifier_citation(block_id, block_index)
                if not is_valid:
                    references_section.append(reason or block_id)
                    continue

            resolved_count += 1

        reasons: List[str] = []
        if resolved_count == 0:
            if unresolved:
                reasons.append(f"unresolved block_ids: {unresolved}")
                stats["rejected_unresolved"] += 1
            if references_section:
                reasons.append(f"in references section: {references_section}")
                stats["rejected_references_section"] += 1
            rejected_fields[field] = reasons
        else:
            gated_data[field] = value
            stats["passed"] += 1

    return {
        "gated_data": gated_data,
        "rejected_fields": rejected_fields,
        "validation_report": stats,
    }


def gate_biblio_extraction(
    extraction_data: Dict[str, Any],
    citations: Dict[str, List[str]],
    block_index: Dict[str, BlockIndexEntry],
) -> Dict[str, Any]:
    """Convenience wrapper for biblio schema extraction.

    Applies evidence gating specifically for biblio fields:
    - title, authors, publication_year, venue: standard gating
    - identifiers: strict gating (anti-References)
    """
    from .schemas.normalized_document import Extraction, Anchor

    anchors: Dict[str, List[Anchor]] = {}
    for field, block_ids in citations.items():
        anchors[field] = []
        for bid in block_ids:
            entry = block_index.get(bid)
            if entry:
                anchors[field].append(
                    Anchor(
                        block_id=entry.block_id,
                        page_index=entry.page_index,
                        bbox=entry.bbox,
                        polygon=entry.polygon,
                    )
                )

    extraction = Extraction(
        data=extraction_data,
        citations=citations,
        anchors=anchors,
    )

    return gate_extraction(
        extraction,
        block_index,
        strict_fields={"identifiers"},
    )


def parse_extraction_schema_json(
    raw_json: str,
) -> Tuple[Dict[str, Any], Dict[str, List[str]]]:
    """Parse extraction_schema_json into data and citations dicts.

    Marker returns fields with `*_citations` suffixes containing source text or block_ids.
    This function separates data from citations.
    """
    import json

    parsed = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
    data: Dict[str, Any] = {}
    citations: Dict[str, List[str]] = {}

    for key, value in parsed.items():
        if key.endswith("_citations"):
            field_name = key[:-10]
            citations[field_name] = value if isinstance(value, list) else []
        else:
            data[key] = value

    return data, citations


def resolve_citation_to_blocks(
    citation_text: str,
    block_index: Dict[str, BlockIndexEntry],
) -> List[str]:
    """Find block IDs that contain the citation text (text-matching fallback)."""
    if not citation_text:
        return []

    citation_lower = citation_text.lower().strip()
    matches = []

    for block_id, entry in block_index.items():
        block_text = (entry.text or entry.html or "").lower()
        block_text = re.sub(r"<[^>]+>", " ", block_text)

        if citation_lower in block_text or block_text in citation_lower:
            matches.append(block_id)

    return matches


def gate_biblio_simple(
    extraction_schema_json: str,
    block_index: Dict[str, BlockIndexEntry],
) -> Dict[str, Any]:
    """Gate biblio extraction with simple {data, citations, gate} output format.

    Args:
        extraction_schema_json: Raw JSON string from Marker API
        block_index: Dict mapping block_id -> BlockIndexEntry

    Returns:
        Dict with:
          - data: Gated field values
          - citations: Original citations per field
          - gate: Per-field pass/fail status
          - anchors: Resolved anchors with bbox/polygon
    """
    data, citations = parse_extraction_schema_json(extraction_schema_json)

    gate: Dict[str, str] = {}
    gated_data: Dict[str, Any] = {}
    anchors: Dict[str, List[Dict[str, Any]]] = {}

    strict_fields = {"identifiers"}

    for field, value in data.items():
        if value is None or (isinstance(value, (list, dict, str)) and not value):
            gated_data[field] = value
            gate[field] = "pass_empty"
            continue

        field_citations = citations.get(field, [])

        if not field_citations:
            gate[field] = "fail_no_citation"
            continue

        resolved = []
        for citation in field_citations:
            if citation.startswith("/page/"):
                entry = block_index.get(citation)
                if entry:
                    resolved.append(
                        {
                            "block_id": citation,
                            "page_index": entry.page_index,
                            "bbox": entry.bbox,
                        }
                    )
            else:
                matched_blocks = resolve_citation_to_blocks(citation, block_index)
                for block_id in matched_blocks[:3]:
                    entry = block_index.get(block_id)
                    if entry:
                        if field in strict_fields:
                            is_valid, _ = validate_identifier_citation(
                                block_id, block_index
                            )
                            if not is_valid:
                                continue
                        resolved.append(
                            {
                                "block_id": block_id,
                                "page_index": entry.page_index,
                                "bbox": entry.bbox,
                                "matched_text": citation[:50],
                            }
                        )

        if not resolved:
            gate[field] = "fail_unresolved"
            continue

        gated_data[field] = value
        gate[field] = "pass"
        anchors[field] = resolved

    return {
        "data": gated_data,
        "citations": citations,
        "gate": gate,
        "anchors": anchors,
    }
