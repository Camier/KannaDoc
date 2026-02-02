"""Verbatim section extraction from chunks.

Extracts Abstract and Keywords sections directly from chunk text,
without LLM paraphrasing. Uses section_hierarchy to identify sections.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .schemas.normalized_document import BlockIndexEntry


ABSTRACT_HEADER_PATTERNS = [
    r"^abstract$",
    r"^summary$",
    r"^r[eé]sum[eé]$",
]

ABSTRACT_INLINE_PATTERN = re.compile(r"^abstract\s*:\s*", re.IGNORECASE)

KEYWORDS_HEADER_PATTERNS = [
    r"^keywords?$",
    r"^key\s*words?$",
    r"^index\s*terms?$",
    r"^mots[- ]cl[eé]s?$",
]

KEYWORDS_INLINE_PATTERN = re.compile(r"^keywords?\s*:\s*", re.IGNORECASE)


def _matches_patterns(text: str, patterns: List[str]) -> bool:
    if not text:
        return False
    text_clean = text.lower().strip()
    text_clean = re.sub(r"<[^>]+>", "", text_clean).strip()
    text_clean = re.sub(r"[:\.\-\s]+$", "", text_clean).strip()
    return any(re.match(pat, text_clean) for pat in patterns)


def _get_header_text(block_id: str, block_index: Dict[str, BlockIndexEntry]) -> str:
    entry = block_index.get(block_id)
    if not entry:
        return ""
    return entry.text or entry.html or ""


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_section_header(
    chunk: Dict[str, Any], patterns: List[str], block_index: Dict[str, BlockIndexEntry]
) -> bool:
    section_hierarchy = chunk.get("section_hierarchy", {})
    if not section_hierarchy:
        return False

    for level, header_block_id in section_hierarchy.items():
        header_text = _get_header_text(header_block_id, block_index)
        if _matches_patterns(header_text, patterns):
            return True

    return False


def extract_abstract(
    blocks: List[Dict[str, Any]],
    block_index: Dict[str, BlockIndexEntry],
) -> Optional[str]:
    """Extract abstract text verbatim from flattened chunk blocks.

    Strategy:
    1. Find blocks under an Abstract/Summary section header (via section_hierarchy)
    2. Fallback: find blocks starting with "Abstract:" inline prefix
    """
    abstract_parts: List[Tuple[int, str]] = []

    for i, block in enumerate(blocks):
        text = block.get("html") or block.get("text", "")
        if not text:
            continue

        clean_text = _strip_html(text)

        if _is_section_header(block, ABSTRACT_HEADER_PATTERNS, block_index):
            abstract_parts.append((i, clean_text))
            continue

        match = ABSTRACT_INLINE_PATTERN.match(clean_text)
        if match:
            content = clean_text[match.end() :].strip()
            if content:
                abstract_parts.append((i, content))

    if not abstract_parts:
        return None

    abstract_parts.sort(key=lambda x: x[0])
    return "\n\n".join(text for _, text in abstract_parts)


def extract_keywords(
    blocks: List[Dict[str, Any]],
    block_index: Dict[str, BlockIndexEntry],
) -> List[str]:
    """Extract keywords verbatim from flattened chunk blocks."""
    keywords_text = ""

    for block in blocks:
        text = block.get("html") or block.get("text", "")
        if not text:
            continue

        clean_text = _strip_html(text)

        if _is_section_header(block, KEYWORDS_HEADER_PATTERNS, block_index):
            keywords_text += " " + clean_text
            continue

        match = KEYWORDS_INLINE_PATTERN.match(clean_text)
        if match:
            content = clean_text[match.end() :].strip()
            if content:
                keywords_text += " " + content

    if not keywords_text.strip():
        return []

    delimiters = r"[;,\|]|\s+-\s+"
    raw_keywords = re.split(delimiters, keywords_text.strip())

    keywords = []
    for kw in raw_keywords:
        kw = kw.strip()
        kw = re.sub(r"^\d+\.\s*", "", kw)
        if kw and len(kw) > 1 and len(kw) < 100:
            keywords.append(kw)

    return keywords


def extract_sections(
    blocks: List[Dict[str, Any]],
    block_index: Dict[str, BlockIndexEntry],
) -> Dict[str, Any]:
    """Extract verbatim sections from flattened chunk blocks."""
    notes: List[str] = []

    abstract = extract_abstract(blocks, block_index)
    if not abstract:
        notes.append("No abstract section found")

    keywords = extract_keywords(blocks, block_index)
    if not keywords:
        notes.append("No keywords section found")

    return {
        "abstract": abstract,
        "keywords": keywords,
        "extraction_notes": notes,
    }
