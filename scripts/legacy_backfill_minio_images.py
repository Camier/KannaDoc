#!/usr/bin/env python3
"""
Legacy Layra (page-images-in-MinIO) backfill script.

Goal
----
Restore the upstream/legacy multimodal assumption:
  - PDFs live in MinIO (already true for the thesis SSOT).
  - Per-page PNGs also live in MinIO (currently missing).
  - Mongo `files.images[*]` must point to existing MinIO image keys.
  - Milvus vectors must reference Mongo images via `image_id` (images_id).

What this script does
---------------------
For a given Knowledge Base (KB):
  1) For files that already have images metadata in Mongo:
       - Re-render pages from the PDF and upload missing PNG objects to MinIO
         using the *existing* `images[*].minio_filename` keys (no Mongo changes).
  2) For files that have no images metadata:
       - Generate page images, upload to MinIO, write `files.images[*]` to Mongo,
         and embed + insert vectors into the KB Milvus collection.

Design notes
------------
- Resumable / idempotent:
  - Existing MinIO objects are skipped (no overwrites).
  - Existing Milvus vectors are detected by `image_id` (images_id) and skipped.
- Keeps memory bounded by rendering pages in small chunks via `convert_from_path`.
- Uses only services inside the running `layra-backend` container.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import tempfile
import uuid
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from bson.objectid import ObjectId
from pdf2image import convert_from_path

from app.core.config import settings
from app.core.logging import logger
from app.db.miniodb import async_minio_manager
from app.db.mongo import get_mongo
from app.db.milvus import milvus_client
from app.db.vector_db import vector_db_client
from app.rag.convert_file import get_pdf_page_count
from app.rag.get_embedding import get_embeddings_from_httpx


@dataclass(frozen=True)
class ImageMeta:
    image_id: str
    minio_key: str
    page_number_1i: int  # 1-indexed page number (Mongo convention)


def _collection_name(kb_id: str) -> str:
    return f"colqwen{kb_id.replace('-', '_')}"


def _make_image_key(username: str, original_filename: str) -> str:
    base = os.path.splitext(original_filename)[0]
    # Matches legacy save_image_to_minio() naming: f"{username}_{base}_{ObjectId()}.png"
    return f"{username}_{base}_{ObjectId()}.png"


def _chunked(seq: Sequence, n: int) -> Iterable[Sequence]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


async def _minio_exists(key: str) -> bool:
    return await async_minio_manager.validate_file_existence(key)


async def _upload_png(key: str, img) -> int:
    """Upload a single PIL image as PNG to MinIO under the provided key."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    await async_minio_manager.upload_image(key, buf)
    return buf.tell()  # not super meaningful after upload, but keeps signature simple


async def _milvus_has_any_rows_for_image_id(collection: str, image_id: str) -> bool:
    rows = milvus_client.client.query(
        collection_name=collection,
        filter=f"image_id == '{image_id}'",
        output_fields=["image_id"],
        limit=1,
    )
    return bool(rows)


async def _milvus_image_ids_present(collection: str, image_ids: List[str]) -> set[str]:
    """Return subset of image_ids that have any rows in Milvus."""
    if not image_ids:
        return set()

    # Chunk query to keep the filter + result size sane.
    present: set[str] = set()
    for batch in _chunked(image_ids, 32):
        # NOTE: python list repr includes quotes => valid Milvus filter
        filter_expr = f"image_id in {list(batch)}"
        rows = milvus_client.client.query(
            collection_name=collection,
            filter=filter_expr,
            output_fields=["image_id"],
            limit=100000,
        )
        present.update(r["image_id"] for r in rows if r.get("image_id"))
    return present


def _sorted_images_from_file_doc(file_doc) -> List[ImageMeta]:
    raw = file_doc.get("images") or []
    metas: List[ImageMeta] = []
    for img in raw:
        try:
            page = int(img.get("page_number"))
        except Exception:
            continue
        image_id = img.get("images_id")
        key = img.get("minio_filename")
        if not image_id or not key or page <= 0:
            continue
        metas.append(ImageMeta(image_id=image_id, minio_key=key, page_number_1i=page))

    metas.sort(key=lambda m: m.page_number_1i)
    return metas


def _is_contiguous_pages(metas: List[ImageMeta]) -> bool:
    if not metas:
        return False
    start = metas[0].page_number_1i
    for i, m in enumerate(metas):
        if m.page_number_1i != start + i:
            return False
    return True


async def backfill_minio_images_for_file(
    *,
    pdf_path: str,
    metas: List[ImageMeta],
    dpi: int,
    chunk_size: int,
    dry_run: bool,
) -> Tuple[int, int]:
    """
    Ensure all `metas[].minio_key` objects exist in MinIO by rendering pages from `pdf_path`.

    Returns:
      (uploaded_count, skipped_existing_count)
    """
    uploaded = 0
    skipped = 0

    # Process in page-order so a partial run is naturally resumable.
    for batch in _chunked(metas, chunk_size):
        # Determine which keys in this batch are missing.
        exists_flags: List[bool] = []
        for m in batch:
            if await _minio_exists(m.minio_key):
                exists_flags.append(True)
                skipped += 1
            else:
                exists_flags.append(False)

        if all(exists_flags):
            continue

        pages = [m.page_number_1i for m in batch]
        contiguous = pages == list(range(pages[0], pages[0] + len(pages)))

        if contiguous:
            imgs = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=pages[0],
                last_page=pages[-1],
                thread_count=1,
            )
            if len(imgs) != len(batch):
                raise RuntimeError(
                    f"Rendered page count mismatch: expected {len(batch)}, got {len(imgs)} "
                    f"(pages {pages[0]}..{pages[-1]})"
                )
            for m, img, exists in zip(batch, imgs, exists_flags):
                if exists:
                    continue
                if dry_run:
                    uploaded += 1
                    continue
                await _upload_png(m.minio_key, img)
                uploaded += 1
        else:
            # Rare case: page numbers in Mongo are non-contiguous.
            # Render per-page to avoid wrong page->key mapping.
            for m, exists in zip(batch, exists_flags):
                if exists:
                    continue
                if dry_run:
                    uploaded += 1
                    continue
                img = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    first_page=m.page_number_1i,
                    last_page=m.page_number_1i,
                    thread_count=1,
                )[0]
                await _upload_png(m.minio_key, img)
                uploaded += 1

    return uploaded, skipped


async def process_file_missing_images_and_vectors(
    *,
    db,
    kb_id: str,
    file_doc,
    dpi: int,
    chunk_size: int,
    dry_run: bool,
) -> None:
    """
    For a file that has no (or partial) `images[]` metadata, generate missing images,
    upload them, create Mongo image metadata, and insert vectors in Milvus.
    """
    file_id = file_doc["file_id"]
    username = file_doc.get("username") or file_id.split("_", 1)[0]
    original_filename = file_doc["filename"]
    pdf_minio_key = file_doc["minio_filename"]
    collection = _collection_name(kb_id)

    logger.info(f"[missing] file_id={file_id} filename={original_filename}")

    pdf_bytes = await async_minio_manager.get_file_from_minio(pdf_minio_key)
    page_count = get_pdf_page_count(pdf_bytes)
    logger.info(f"[missing] pages={page_count} dpi={dpi} collection={collection}")

    # Planning mode: don't render/compute embeddings, just report what would be done.
    if dry_run:
        existing = len(_sorted_images_from_file_doc(file_doc))
        to_create = max(0, page_count - existing)
        logger.info(
            f"[dry-run] would ensure {existing} existing pages + create {to_create} new pages "
            f"(upload PNGs, add Mongo images, insert Milvus vectors)"
        )
        return

    # Persist PDF to a temp file so we can render pages without re-writing bytes per call.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        pdf_path = tmp.name

    try:
        # Build a map of already-present image metas from Mongo (supports resume).
        existing_metas = _sorted_images_from_file_doc(file_doc)
        by_page: dict[int, ImageMeta] = {m.page_number_1i: m for m in existing_metas}

        # Determine which existing image_ids are already embedded.
        present_image_ids = await _milvus_image_ids_present(
            collection, [m.image_id for m in existing_metas]
        )

        for start_page in range(1, page_count + 1, chunk_size):
            end_page = min(start_page + chunk_size - 1, page_count)

            # Render this range once.
            imgs = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=start_page,
                last_page=end_page,
                thread_count=1,
            )
            expected = end_page - start_page + 1
            if len(imgs) != expected:
                raise RuntimeError(
                    f"Rendered page count mismatch: expected {expected}, got {len(imgs)} "
                    f"(pages {start_page}..{end_page})"
                )

            batch_image_ids: List[str] = []
            batch_page_numbers_1i: List[int] = []
            batch_buffers: List[io.BytesIO] = []

            for i, img in enumerate(imgs):
                page_1i = start_page + i

                meta = by_page.get(page_1i)
                if meta:
                    image_id = meta.image_id
                    image_key = meta.minio_key
                    already_embedded = image_id in present_image_ids
                else:
                    image_id = f"{username}_{uuid.uuid4()}"
                    image_key = _make_image_key(username, original_filename)
                    already_embedded = False

                # Ensure PNG exists in MinIO.
                if not await _minio_exists(image_key):
                    if not dry_run:
                        await _upload_png(image_key, img)

                # Ensure Mongo image metadata exists (must exist before vectors to avoid
                # the retrieval path deleting vectors when image_id is missing).
                if not meta:
                    if not dry_run:
                        await db.add_images(
                            file_id=file_id,
                            images_id=image_id,
                            minio_filename=image_key,
                            minio_url="",  # URLs are generated on-demand in API endpoints
                            page_number=page_1i,
                        )
                    # update local map so resume within same run works
                    by_page[page_1i] = ImageMeta(
                        image_id=image_id, minio_key=image_key, page_number_1i=page_1i
                    )

                # Skip embedding if already present in Milvus
                if already_embedded:
                    continue

                # Prepare for embedding+insert
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                batch_buffers.append(buf)
                batch_image_ids.append(image_id)
                batch_page_numbers_1i.append(page_1i)

            if not batch_buffers:
                continue

            if dry_run:
                continue

            # Embed this batch
            files = []
            for page_1i, buf in zip(batch_page_numbers_1i, batch_buffers):
                files.append(
                    (
                        "images",
                        (f"{original_filename}_{page_1i}.png", buf, "image/png"),
                    )
                )
            embeddings = await get_embeddings_from_httpx(files, endpoint="embed_image")
            if len(embeddings) != len(batch_buffers):
                raise RuntimeError(
                    f"Embedding count mismatch: expected {len(batch_buffers)}, got {len(embeddings)}"
                )

            # Insert to Milvus (page_number is 0-indexed in existing data)
            for emb, image_id, page_1i in zip(
                embeddings, batch_image_ids, batch_page_numbers_1i
            ):
                vector_db_client.insert(
                    {
                        "colqwen_vecs": emb,
                        "page_number": page_1i - 1,
                        "image_id": image_id,
                        "file_id": file_id,
                    },
                    collection,
                )
                present_image_ids.add(image_id)

            for buf in batch_buffers:
                try:
                    buf.close()
                except Exception:
                    pass

    finally:
        try:
            os.unlink(pdf_path)
        except Exception:
            pass


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb-id", required=True, help="Knowledge base id to backfill")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=4,
        help="Pages to render per batch (keeps memory bounded)",
    )
    parser.add_argument(
        "--only-file-id",
        help="Process only a single file_id (useful for smoke tests / resume)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        help="Limit to first N files (useful for smoke tests)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan only; do not write to MinIO/Mongo/Milvus",
    )
    args = parser.parse_args()

    kb_id = args.kb_id
    chunk_size = max(1, int(args.chunk_size))
    dpi = int(getattr(settings, "embedding_image_dpi", 150))

    db = await get_mongo()
    kb = await db.get_knowledge_base_by_id(kb_id, include_deleted=True)
    if not kb:
        print(f"KB not found: {kb_id}")
        return 2

    file_ids = [f.get("file_id") for f in (kb.get("files") or []) if f.get("file_id")]
    if args.only_file_id:
        file_ids = [fid for fid in file_ids if fid == args.only_file_id]
    if args.max_files is not None:
        file_ids = file_ids[: max(0, int(args.max_files))]
    files = await db.db.files.find(
        {"file_id": {"$in": file_ids}, "is_delete": False},
        {"file_id": 1, "filename": 1, "username": 1, "minio_filename": 1, "images": 1},
    ).to_list(length=None)

    files_by_id = {f["file_id"]: f for f in files}

    uploaded_total = 0
    skipped_total = 0
    missing_files: List[str] = []
    failures: List[Tuple[str, str]] = []

    for fid in file_ids:
        file_doc = files_by_id.get(fid)
        if not file_doc:
            missing_files.append(fid)
            continue
        try:
            images = _sorted_images_from_file_doc(file_doc)
            if not images:
                # New/missing-image file: generate images+mongo metadata + embed vectors.
                await process_file_missing_images_and_vectors(
                    db=db,
                    kb_id=kb_id,
                    file_doc=file_doc,
                    dpi=dpi,
                    chunk_size=chunk_size,
                    dry_run=args.dry_run,
                )
                continue

            # Existing file: only backfill missing MinIO objects (no Mongo/Milvus writes).
            logger.info(
                f"[backfill] file_id={fid} pages={len(images)} filename={file_doc.get('filename')}"
            )
            pdf_bytes = await async_minio_manager.get_file_from_minio(
                file_doc["minio_filename"]
            )
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                pdf_path = tmp.name
            try:
                up, sk = await backfill_minio_images_for_file(
                    pdf_path=pdf_path,
                    metas=images,
                    dpi=dpi,
                    chunk_size=chunk_size,
                    dry_run=args.dry_run,
                )
                uploaded_total += up
                skipped_total += sk
            finally:
                try:
                    os.unlink(pdf_path)
                except Exception:
                    pass
        except Exception as e:
            failures.append((fid, str(e)))
            logger.exception(f"[error] file_id={fid} failed")
            # Continue so a single problematic PDF doesn't block the whole SSOT rebuild.
            continue

    print("KB_ID", kb_id)
    print("FILES_IN_KB", len(file_ids))
    if missing_files:
        print("MISSING_FILE_DOCS", len(missing_files))
    if failures:
        print("FAILED_FILES", len(failures))
    print("DPI", dpi)
    print("CHUNK_SIZE", chunk_size)
    print("DRY_RUN", bool(args.dry_run))
    print("MINIO_IMAGES_TO_UPLOAD", uploaded_total)
    print("MINIO_IMAGES_ALREADY_PRESENT", skipped_total)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
