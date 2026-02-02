"""Build block index and resolve citations to anchors."""

from typing import Any, Dict, List, Optional
from .schemas.normalized_document import BlockIndexEntry, Anchor


def _normalize_bbox(block: Dict) -> Optional[List[float]]:
    """Extract bbox from block in various formats."""
    bbox = block.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        return [float(x) for x in bbox]

    # Marker OSS format: polygon.bbox
    poly = block.get("polygon")
    if isinstance(poly, dict) and isinstance(poly.get("bbox"), list):
        bbox = poly["bbox"]
        if len(bbox) == 4:
            return [float(x) for x in bbox]

    return None


def _normalize_polygon(block: Dict) -> Optional[List[List[float]]]:
    """Extract polygon points from block."""
    poly = block.get("polygon")
    if isinstance(poly, list):
        return [[float(p[0]), float(p[1])] for p in poly if len(p) >= 2]
    if isinstance(poly, dict) and isinstance(poly.get("polygon"), list):
        return [[float(p[0]), float(p[1])] for p in poly["polygon"] if len(p) >= 2]
    return None


def _parse_page_from_block_id(block_id: str) -> Optional[int]:
    """Parse page index from block_id path like '/page/0/Text/1'.

    CRITICAL: Real data shows block_ids like '/page/0/Text/1'.
    The page number is the second path component.
    """
    import re

    match = re.match(r"^/page/(\d+)/", block_id)
    if match:
        return int(match.group(1))
    return None


def build_block_index(marker_json: Any) -> Dict[str, BlockIndexEntry]:
    """
    Build index from Marker JSON structure.
    Returns: {block_id: BlockIndexEntry}

    NOTE: page_index derivation strategy:
    1. Try block.page_id if present
    2. Try parsing from block_id path (/page/N/...)
    3. Inherit from parent during tree traversal
    4. Default to None (acceptable for non-critical blocks)
    """
    index: Dict[str, BlockIndexEntry] = {}

    def visit(
        block: Any, page_index: Optional[int] = None, parent_id: Optional[str] = None
    ):
        if not isinstance(block, dict):
            return

        block_id = str(block.get("id") or block.get("block_id") or "")
        if not block_id:
            return

        # Strategy 1: Extract page_id if present
        if "page_id" in block and block["page_id"] is not None:
            try:
                page_index = int(block["page_id"])
            except (ValueError, TypeError):
                pass

        # Strategy 2: Parse from block_id path
        if page_index is None:
            page_index = _parse_page_from_block_id(block_id)

        entry = BlockIndexEntry(
            block_id=block_id,
            page_index=page_index,
            block_type=block.get("block_type"),
            bbox=_normalize_bbox(block),
            polygon=_normalize_polygon(block),
            text=block.get("text"),
            html=block.get("html"),
            parent_block_id=parent_id,
        )
        index[block_id] = entry

        # Recurse into children (page_index inherited)
        for child in block.get("children", []) or []:
            visit(child, page_index=page_index, parent_id=block_id)

    # Handle both list (pages) and dict (with children) formats
    if isinstance(marker_json, list):
        for i, page_block in enumerate(marker_json):
            visit(page_block, page_index=i, parent_id=None)
    elif isinstance(marker_json, dict):
        for child in marker_json.get("children", []) or []:
            visit(child, page_index=None, parent_id=None)

    return index


def resolve_anchors(
    citations: Dict[str, List[str]], block_index: Dict[str, BlockIndexEntry]
) -> Dict[str, List[Anchor]]:
    """Resolve citation block IDs to anchors with bbox."""
    anchors: Dict[str, List[Anchor]] = {}

    for field, block_ids in citations.items():
        anchors[field] = []
        for bid in block_ids:
            entry = block_index.get(str(bid))
            if entry:
                anchors[field].append(
                    Anchor(
                        block_id=entry.block_id,
                        page_index=entry.page_index,
                        bbox=entry.bbox,
                        polygon=entry.polygon,
                    )
                )
            else:
                # Block not found - store ID anyway for debugging
                anchors[field].append(
                    Anchor(block_id=str(bid), page_index=None, bbox=None, polygon=None)
                )

    return anchors
