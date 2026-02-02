"""Transform RawMarkerEnvelope to NormalizedDocumentV2."""

import base64
import hashlib
import imghdr
import json
import logging
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .schemas.raw_envelope import RawMarkerEnvelope
from .schemas.normalized_document import (
    NormalizedDocumentV2,
    NormalizedChunk,
    Extraction,
    BlockIndexEntry,
    Anchor,
    ChunkProvenance,
    ImageAsset,
    FigureRecord,
)
from .block_index import build_block_index, resolve_anchors
from .datalab_utils import calculate_sha256_string

logger = logging.getLogger(__name__)


def coerce_json_maybe(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def parse_extraction_schema_json(
    raw_value: Optional[Union[str, dict]],
) -> Tuple[Dict, Dict, List[str]]:
    if not raw_value:
        return {}, {}, ["extraction_schema_json is empty"]

    if isinstance(raw_value, dict):
        parsed = raw_value
    elif isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as e:
            return {}, {}, [f"JSON parse error: {e}"]
    else:
        return {}, {}, [f"Unexpected type: {type(raw_value).__name__}"]

    data: Dict[str, Any] = {}
    citations: Dict[str, List[str]] = {}

    for key, value in parsed.items():
        if key.endswith("_citations") and isinstance(value, list):
            base_field = key[: -len("_citations")]
            citations[base_field] = [str(bid) for bid in value]
        else:
            data[key] = value

    return data, citations, []


def filter_raw_for_storage(raw: dict) -> dict:
    KEEP_FIELDS = {
        "json",
        "chunks",
        "extraction_schema_json",
        "status",
        "metadata",
        "request_id",
        "page_count",
        "success",
    }
    return {k: v for k, v in raw.items() if k in KEEP_FIELDS}


def html_to_text(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


FIGURE_BLOCK_TYPES = {"Figure", "Picture", "Image", "PictureGroup", "FigureGroup"}
CAPTION_BLOCK_TYPES = {"Caption"}

_IMG_FILENAME_RE = re.compile(
    r"([A-Za-z0-9_.\-/]+\.(?:png|jpg|jpeg|webp|gif|tiff|bmp))", re.IGNORECASE
)


def _strip_data_uri_prefix(b64: str) -> str:
    if not isinstance(b64, str):
        return b64
    if b64.startswith("data:") and "base64," in b64:
        return b64.split("base64,", 1)[1]
    return b64


def _decode_image_payload(payload: Any) -> Optional[bytes]:
    if payload is None:
        return None
    if isinstance(payload, (bytes, bytearray)):
        return bytes(payload)
    if isinstance(payload, str):
        try:
            return base64.b64decode(_strip_data_uri_prefix(payload), validate=False)
        except Exception:
            return None
    return None


def _sniff_ext(filename: str, data: bytes) -> str:
    if isinstance(filename, str) and "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()
        if ext in {"png", "jpg", "jpeg", "webp", "gif", "tiff", "bmp"}:
            return "jpg" if ext == "jpeg" else ext
    kind = imghdr.what(None, h=data)
    if kind:
        return "jpg" if kind == "jpeg" else kind
    return "bin"


def collect_images_from_json(marker_json: Any) -> Dict[str, str]:
    """Extract per-block images from Marker JSON structure.

    Marker stores images at block level: block.images = {filename: base64}
    This collects all into a single dict for unified processing.
    """
    collected: Dict[str, str] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "images" in node and isinstance(node["images"], dict):
                for fname, b64 in node["images"].items():
                    if fname and b64 and fname not in collected:
                        collected[fname] = b64
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(marker_json)
    return collected


def normalize_images_with_persistence(
    raw_images: Any,
    asset_dir: Path,
) -> Tuple[List[ImageAsset], Dict[str, str], List[str]]:
    errors: List[str] = []
    assets: List[ImageAsset] = []
    filename_to_asset_id: Dict[str, str] = {}

    if not raw_images:
        return assets, filename_to_asset_id, errors

    raw_images = coerce_json_maybe(raw_images)
    if not isinstance(raw_images, dict):
        return (
            assets,
            filename_to_asset_id,
            [f"Unexpected images type: {type(raw_images)}"],
        )

    asset_dir.mkdir(parents=True, exist_ok=True)

    for filename, payload in raw_images.items():
        data = _decode_image_payload(payload)
        if not data:
            errors.append(f"Failed to decode image: {filename}")
            continue

        sha = hashlib.sha256(data).hexdigest()
        ext = _sniff_ext(str(filename), data)
        out_name = f"{sha}.{ext}"
        out_path = asset_dir / out_name

        if not out_path.exists():
            try:
                out_path.write_bytes(data)
            except Exception as e:
                errors.append(f"Failed to write image {filename}: {e}")
                continue

        asset_id = f"sha256:{sha}"
        mime, _ = mimetypes.guess_type(filename)
        filename_to_asset_id[str(filename)] = asset_id

        assets.append(
            ImageAsset(
                asset_id=asset_id,
                filename=str(filename),
                mime=mime or "application/octet-stream",
                byte_size=len(data),
                storage_uri=str(out_path),
            )
        )

    return assets, filename_to_asset_id, errors


def extract_image_filenames_from_html(html: str) -> List[str]:
    if not html:
        return []
    found = _IMG_FILENAME_RE.findall(html)
    seen: Set[str] = set()
    out: List[str] = []
    for f in found:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _guess_image_filename_from_block_id(
    block_id: str, known_filenames: Set[str]
) -> Optional[str]:
    m = re.match(r"^/page/(\d+)/([A-Za-z0-9_]+)/(\d+)", str(block_id))
    if not m:
        return None
    page, kind, idx = m.group(1), m.group(2), m.group(3)
    candidates = [
        f"_page_{page}_{kind}_{idx}.jpeg",
        f"_page_{page}_{kind}_{idx}.jpg",
        f"_page_{page}_{kind}_{idx}.png",
        f"_page_{page}_{kind}_{idx}.webp",
    ]
    for c in candidates:
        if c in known_filenames:
            return c
    return None


def find_nearest_caption(
    figure_block: BlockIndexEntry,
    block_index: Dict[str, BlockIndexEntry],
) -> Optional[BlockIndexEntry]:
    if figure_block.page_index is None:
        return None

    fig_page = figure_block.page_index
    fig_bottom = 0.0
    if figure_block.bbox and len(figure_block.bbox) >= 4:
        fig_bottom = float(figure_block.bbox[1]) + float(figure_block.bbox[3])

    best_caption: Optional[BlockIndexEntry] = None
    best_score: Optional[float] = None

    for entry in block_index.values():
        if entry.block_type not in CAPTION_BLOCK_TYPES:
            continue
        if entry.page_index != fig_page:
            continue
        if not entry.bbox or len(entry.bbox) < 2:
            continue

        caption_top = float(entry.bbox[1])
        same_parent_bonus = (
            -0.1
            if (
                figure_block.parent_block_id
                and entry.parent_block_id
                and figure_block.parent_block_id == entry.parent_block_id
            )
            else 0.0
        )

        if caption_top >= fig_bottom:
            gap = caption_top - fig_bottom
            score = gap + same_parent_bonus
        else:
            score = abs(caption_top - fig_bottom) + 10.0 + same_parent_bonus

        if best_score is None or score < best_score:
            best_score = score
            best_caption = entry

    return best_caption


def normalize_figures(
    doc_id: str,
    block_index: Dict[str, BlockIndexEntry],
    filename_to_asset_id: Dict[str, str],
) -> List[FigureRecord]:
    figures: List[FigureRecord] = []
    known_filenames = set(filename_to_asset_id.keys())
    fig_counter = 0

    for block_id, entry in block_index.items():
        if entry.block_type not in FIGURE_BLOCK_TYPES:
            continue

        html = entry.html or ""
        fnames = extract_image_filenames_from_html(html)
        asset_ids = [
            filename_to_asset_id[f] for f in fnames if f in filename_to_asset_id
        ]

        if not asset_ids and known_filenames:
            guessed = _guess_image_filename_from_block_id(block_id, known_filenames)
            if guessed and guessed in filename_to_asset_id:
                fnames = [guessed]
                asset_ids = [filename_to_asset_id[guessed]]

        caption_entry = find_nearest_caption(entry, block_index)
        caption_text = (
            html_to_text(caption_entry.html or caption_entry.text or "")
            if caption_entry
            else None
        )
        caption_block_id = caption_entry.block_id if caption_entry else None

        image_asset_id = asset_ids[0] if asset_ids else None

        figures.append(
            FigureRecord(
                figure_id=f"{doc_id}/fig/{fig_counter:04d}",
                doc_id=doc_id,
                block_id=block_id,
                page_index=entry.page_index,
                bbox=entry.bbox,
                polygon=entry.polygon,
                caption_text=caption_text,
                caption_block_id=caption_block_id,
                image_asset_id=image_asset_id,
                section_hierarchy=None,
            )
        )
        fig_counter += 1

    return figures


def normalize_chunks(
    raw_chunks: Any,
    doc_id: str,
    provenance: ChunkProvenance,
    block_index: Dict[str, BlockIndexEntry],
    filename_to_asset_id: Optional[Dict[str, str]] = None,
) -> List[NormalizedChunk]:
    normalized: List[NormalizedChunk] = []
    raw_chunks = coerce_json_maybe(raw_chunks)

    blocks = raw_chunks
    if isinstance(raw_chunks, dict):
        blocks = raw_chunks.get("blocks", [])
    if not isinstance(blocks, list):
        return []

    for i, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue

        html = block.get("html", "")
        text = html_to_text(html)

        if not text or len(text) < 10:
            continue

        block_id = block.get("id") or block.get("chunk_id") or f"chunk_{i}"
        page = block.get("page", 0)

        chunk_id = (
            block.get("chunk_id")
            or calculate_sha256_string(
                f"{doc_id}|{block_id}|{calculate_sha256_string(html)}"
            )[:32]
        )

        block_id_str = str(block_id)
        block_entry = block_index.get(block_id_str)
        anchors_list: List[Dict[str, Any]] = []
        if block_entry:
            anchors_list.append(
                {
                    "block_id": block_entry.block_id,
                    "page_index": block_entry.page_index,
                    "bbox": block_entry.bbox,
                    "polygon": block_entry.polygon,
                }
            )

        image_filenames = extract_image_filenames_from_html(html)
        image_asset_ids: List[str] = []
        if filename_to_asset_id and image_filenames:
            image_asset_ids = [
                filename_to_asset_id[f]
                for f in image_filenames
                if f in filename_to_asset_id
            ]

        normalized.append(
            NormalizedChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=text,
                html=html,
                page_refs=[page] if isinstance(page, int) else [0],
                block_ids=[block_id_str],
                embeddings_meta={},
                graph_meta={
                    "section_hierarchy": block.get("section_hierarchy"),
                    "block_type": block.get("block_type"),
                    "anchors": anchors_list,
                    "image_filenames": image_filenames,
                    "image_asset_ids": image_asset_ids,
                },
                provenance=provenance,
            )
        )

    return normalized


def normalize_document(
    envelope: RawMarkerEnvelope,
    assets_root: Optional[Path] = None,
) -> NormalizedDocumentV2:
    raw = envelope.raw_result

    marker_json = coerce_json_maybe(raw.get("json"))
    block_index_dict = build_block_index(marker_json) if marker_json else {}
    block_index_list = list(block_index_dict.values())

    extraction_val = coerce_json_maybe(raw.get("extraction_schema_json"))
    data, citations, errors = parse_extraction_schema_json(extraction_val)

    anchors = resolve_anchors(citations, block_index_dict) if citations else {}

    extraction = Extraction(
        data=data,
        citations=citations,
        anchors=anchors,
        raw_extraction_schema_json=raw.get("extraction_schema_json"),
        parse_errors=errors,
    )

    chunk_provenance = ChunkProvenance(
        source_url=getattr(envelope.provenance, "source_url", None),
        retrieved_at=envelope.provenance.retrieved_at,
        license=getattr(envelope.provenance, "license", "unknown"),
        collector_id=envelope.provenance.collector_id,
        ingest_batch=envelope.provenance.ingest_batch,
    )

    if assets_root is None:
        assets_root = Path.cwd() / "_assets" / envelope.doc_id
    images_dir = assets_root / "images"

    top_level_images = raw.get("images") or {}
    per_block_images = collect_images_from_json(marker_json) if marker_json else {}
    all_images = {**per_block_images, **top_level_images}

    images_debug = {
        "top_level_count": len(top_level_images),
        "per_block_count": len(per_block_images),
        "total_collected": len(all_images),
    }

    image_assets, filename_to_asset_id, image_errors = (
        normalize_images_with_persistence(all_images, images_dir)
    )

    images_debug["persisted_count"] = len(image_assets)
    images_debug["error_count"] = len(image_errors)

    figures = normalize_figures(envelope.doc_id, block_index_dict, filename_to_asset_id)

    raw_chunks = coerce_json_maybe(raw.get("chunks"))
    chunks = normalize_chunks(
        raw_chunks,
        envelope.doc_id,
        chunk_provenance,
        block_index_dict,
        filename_to_asset_id=filename_to_asset_id,
    )

    filtered_raw = filter_raw_for_storage(raw)
    filtered_raw["assets"] = {
        "assets_root": str(assets_root),
        "images": [a.model_dump() for a in image_assets],
        "figures": [f.model_dump() for f in figures],
        "image_errors": image_errors,
        "images_debug": images_debug,
    }

    return NormalizedDocumentV2(
        doc_id=envelope.doc_id,
        metadata=data,
        provenance=chunk_provenance,
        datalab=envelope.datalab.model_dump(),
        raw=filtered_raw,
        block_index=block_index_list,
        extraction=extraction,
        chunks=chunks,
        images=image_assets,
        figures=figures,
    )
