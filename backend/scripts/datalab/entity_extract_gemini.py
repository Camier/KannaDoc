#!/usr/bin/env python3

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import warnings

warnings.warn(
    "entity_extract_gemini.py is deprecated. Use extract_entities_v2.py instead.",
    DeprecationWarning,
    stacklevel=2,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

ENTITY_TYPES = [
    "Compound",
    "Plant",
    "Effect",
    "Disease",
    "Dosage",
    "Mechanism",
    "TraditionalUse",
    "Population",
    "Legal",
]

ENTITY_EXTRACTION_PROMPT = """Extract entities from this scientific text about ethnopharmacology.

Text: {text}

Extract the following entity types:
- Compound: Chemical compounds, alkaloids, molecules (e.g., mesembrine, mesembrenone)
- Plant: Plant species - scientific and common names (e.g., Sceletium tortuosum, Kanna)
- Effect: Pharmacological/therapeutic effects (e.g., anxiolytic, antidepressant, anti-inflammatory)
- Disease: Medical conditions, disorders, symptoms (e.g., depression, anxiety, inflammation)
- Dosage: Dosage information with amounts and units (e.g., 25mg daily, 100-200mg)
- Mechanism: Molecular targets, receptors, pathways (e.g., SERT inhibitor, PDE4, MAO-A, 5-HT reuptake)
- TraditionalUse: Historical/cultural medicinal uses by indigenous peoples (e.g., Khoisan use for mood, chewing for thirst)
- Population: Ethnic groups, geographic regions, demographics (e.g., San people, South Africa, elderly patients)
- Legal: Regulatory status, legal considerations, scheduling (e.g., GRAS status, controlled substance, patent)

Return JSON array of entities:
[
  {{"entity_type": "Compound", "entity_name": "...", "context": "..."}},
  ...
]

Rules:
- Extract ALL relevant entities from the text
- For context, include a brief phrase showing where the entity appears
- Normalize plant names to scientific format when possible
- Be precise with compound names (full chemical names)
- For Mechanism, capture specific molecular targets (receptors, enzymes, transporters)
- For TraditionalUse, capture the cultural context and purpose
- Return empty array [] if no entities found
- Return ONLY the JSON array, no additional text or markdown blocks."""


class GeminiEntityExtractor:
    def __init__(
        self, base_url: str, api_key: str, model: str, min_request_interval: float
    ):
        import openai

        self.client = openai.OpenAI(
            base_url=base_url, api_key=api_key, max_retries=5, timeout=60.0
        )
        self.model = model
        self._last_request_time = 0
        self._min_request_interval = max(0.0, float(min_request_interval))

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        if not text or len(text.strip()) < 20:
            return []

        self._rate_limit()

        max_chars = 12000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in ethnopharmacology. Extract entities precisely and return valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )

            content = (response.choices[0].message.content or "").strip()
            return self._parse_json_response(content)

        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return []

    def _parse_json_response(self, content: str) -> List[Dict[str, Any]]:
        try:
            result = json.loads(content)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        array_match = re.search(r"\[[\s\S]*\]", content)
        if array_match:
            try:
                result = json.loads(array_match.group(0))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        return []


def compute_chunk_id(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def load_chunks_from_normalized(normalized_file: Path) -> List[Dict[str, Any]]:
    if not normalized_file.exists():
        return []
    try:
        with open(normalized_file) as f:
            data = json.load(f)
            return data.get("chunks", [])
    except Exception as e:
        logger.error(f"Failed to load {normalized_file}: {e}")
        return []


def process_doc_dir(
    doc_dir: Path,
    base_url: str,
    api_key: str,
    model: str,
    min_request_interval: float,
    max_workers: int = 4,
) -> Optional[Dict[str, Any]]:
    entities_file = doc_dir / "entities.json"

    def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
        tmp_file = path.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_file, path)

    existing: Optional[Dict[str, Any]] = None
    if entities_file.exists():
        try:
            with open(entities_file) as f:
                existing = json.load(f)
        except Exception as e:
            logger.warning(
                f"Failed to read existing entities.json for {doc_dir.name}: {e}. Rebuilding."
            )
            existing = None

        # Resume only if prior run marked it partial; otherwise skip.
        if isinstance(existing, dict) and existing.get("status") != "partial":
            logger.info(f"Skipping {doc_dir.name} - entities.json already exists")
            return None

    normalized_file = doc_dir / "normalized.json"
    if not normalized_file.exists():
        logger.warning(f"Skipping {doc_dir.name} - normalized.json not found")
        return None

    logger.info(f"Processing: {doc_dir.name} with {max_workers} chunk workers")
    chunks = load_chunks_from_normalized(normalized_file)

    doc_id = doc_dir.name
    try:
        with open(normalized_file) as f:
            data = json.load(f)
            doc_id = data.get("doc_id", doc_dir.name)
    except:
        pass

    chunk_entities = []
    total_entities = 0

    processed_chunk_ids = set()
    models_used = []
    if isinstance(existing, dict):
        prior_models = existing.get("models_used")
        if isinstance(prior_models, list):
            models_used = [str(m) for m in prior_models if m]
        elif existing.get("model"):
            models_used = [str(existing.get("model"))]

        prior = existing.get("chunk_entities")
        if isinstance(prior, list):
            for item in prior:
                if isinstance(item, dict) and item.get("chunk_id"):
                    processed_chunk_ids.add(item["chunk_id"])
            chunk_entities = [
                x for x in prior if isinstance(x, dict) and x.get("chunk_id")
            ]
            total_entities = sum(
                len(x.get("entities") or [])
                for x in chunk_entities
                if isinstance(x.get("entities"), list)
            )
            logger.info(
                f"Resuming {doc_dir.name} from {len(processed_chunk_ids)} processed chunks"
            )

    # Prepare chunks to process
    chunks_to_process = []
    for chunk in chunks:
        text = chunk.get("text", "") or chunk.get("content", "")
        if not text and "html" in chunk:
            text = re.sub(r"<[^>]+>", " ", chunk["html"])
            text = re.sub(r"\s+", " ", text).strip()

        if not text or len(text.strip()) < 50:
            continue

        chunk_id = chunk.get("id") or chunk.get("chunk_id") or compute_chunk_id(text)

        if chunk_id in processed_chunk_ids:
            continue

        chunks_to_process.append({"chunk_id": chunk_id, "text": text})

    if not chunks_to_process:
        # Check if we just need to finalize
        if len(processed_chunk_ids) > 0:
            if model and model not in models_used:
                models_used.append(model)
            result = {
                "doc_id": doc_id,
                "chunk_entities": chunk_entities,
                "total_entities": total_entities,
                "extraction_date": datetime.now(timezone.utc).isoformat(),
                "status": "complete",
                "model": model,
                "models_used": models_used,
                "processed_chunks": len(processed_chunk_ids),
                "total_chunks": len(chunks),
            }
            _atomic_write_json(entities_file, result)
            logger.info(f"Finished {doc_dir.name}: {total_entities} entities found")
            return result
        return None

    # Checkpointing lock
    import threading

    lock = threading.Lock()
    checkpoint_every = 25
    new_processed_since_checkpoint = 0
    completed_count = 0

    def process_chunk_wrapper(item):
        # Instantiate extractor per thread/task to avoid shared rate limiter lock contention
        # if we want independent workers.
        # Alternatively, we could reuse one if we wanted strict global rate limiting.
        # Here we assume we want parallelism.
        local_extractor = GeminiEntityExtractor(
            base_url, api_key, model, min_request_interval=min_request_interval
        )
        entities = local_extractor.extract_entities(item["text"])
        return {"chunk_id": item["chunk_id"], "entities": entities}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_chunk_wrapper, item): item
            for item in chunks_to_process
        }

        # Use tqdm if possible, but we are running in background usually.
        # We'll just log periodically.
        total_to_do = len(chunks_to_process)

        for future in as_completed(futures):
            try:
                result = future.result()
                ents = result["entities"]

                with lock:
                    if ents:
                        chunk_entities.append(
                            {"chunk_id": result["chunk_id"], "entities": ents}
                        )
                        total_entities += len(ents)

                    processed_chunk_ids.add(result["chunk_id"])
                    new_processed_since_checkpoint += 1
                    completed_count += 1

                    current_processed = len(processed_chunk_ids)

                    if completed_count % 10 == 0:
                        logger.info(
                            f"  Processed {current_processed}/{len(chunks)} chunks, found {total_entities} entities"
                        )

                    if new_processed_since_checkpoint >= checkpoint_every:
                        if model and model not in models_used:
                            models_used.append(model)

                        # Sort chunk_entities by chunk_id for consistency (optional but good)
                        # Actually keeping append order is fine, or sort by original index if needed.

                        payload = {
                            "doc_id": doc_id,
                            "chunk_entities": chunk_entities,
                            "total_entities": total_entities,
                            "extraction_date": datetime.now(timezone.utc).isoformat(),
                            "status": "partial",
                            "model": model,
                            "models_used": models_used,
                            "processed_chunks": current_processed,
                            "total_chunks": len(chunks),
                        }
                        _atomic_write_json(entities_file, payload)
                        new_processed_since_checkpoint = 0

            except Exception as e:
                logger.error(f"Error processing chunk: {e}")

    # Final save
    if model and model not in models_used:
        models_used.append(model)
    result = {
        "doc_id": doc_id,
        "chunk_entities": chunk_entities,
        "total_entities": total_entities,
        "extraction_date": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "model": model,
        "models_used": models_used,
        "processed_chunks": len(processed_chunk_ids),
        "total_chunks": len(chunks),
    }
    _atomic_write_json(entities_file, result)

    logger.info(f"Finished {doc_dir.name}: {total_entities} entities found")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract entities using Gemini 2.5 Flash"
    )
    parser.add_argument("--test", type=str, help="Test extraction on provided text")
    parser.add_argument(
        "--input-dir",
        type=str,
        default="data/extractions/prod_max/",
        help="Base directory",
    )
    parser.add_argument("--limit", type=int, help="Limit number of documents")
    parser.add_argument(
        "--model", type=str, default="gemini-2.5-flash", help="Model name"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="OpenAI-compatible base URL (overrides env).",
    )
    parser.add_argument(
        "--api-key-env",
        type=str,
        default=None,
        help="Environment variable name containing API key (overrides env selection).",
    )
    parser.add_argument(
        "--min-request-interval",
        type=float,
        default=None,
        help="Minimum seconds between requests (default: 1.5 for localhost:8317, else 0.0).",
    )
    parser.add_argument(
        "--chunk-workers",
        type=int,
        default=4,
        help="Parallel workers per document (default: 4)",
    )
    parser.add_argument(
        "--doc-workers",
        type=int,
        default=8,
        help="Concurrent documents to process (default: 8)",
    )

    args = parser.parse_args()

    base_url = (
        args.base_url
        or os.getenv("ZHIPUAI_CODING_BASE")
        or os.getenv("OPENAI_BASE_URL")
        or "http://localhost:8317/v1"
    )
    api_key = None
    if args.api_key_env:
        api_key = os.getenv(args.api_key_env)
    if not api_key:
        api_key = os.getenv("ZHIPUAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = "layra-cliproxyapi-key"

    min_request_interval = args.min_request_interval
    if min_request_interval is None:
        if "localhost:8317" in (base_url or ""):
            min_request_interval = 1.5
        else:
            min_request_interval = 0.0

    extractor = GeminiEntityExtractor(
        base_url, api_key, args.model, min_request_interval=min_request_interval
    )

    if args.test:
        logger.info(f"Test mode: {args.test}")
        entities = extractor.extract_entities(args.test)
        result = {
            "test_input": args.test,
            "entities": entities,
            "total_entities": len(entities),
        }
        print(json.dumps(result, indent=2))
        return

    input_path = Path(args.input_dir)
    if not input_path.exists():
        logger.error(f"Input directory not found: {input_path}")
        sys.exit(1)

    doc_dirs = sorted(
        [
            d
            for d in input_path.iterdir()
            if d.is_dir() and (d / "normalized.json").exists()
        ]
    )
    if args.limit:
        doc_dirs = doc_dirs[: args.limit]

    logger.info(f"Found {len(doc_dirs)} documents to process")
    logger.info(
        f"Configuration: {args.doc_workers} doc workers, {args.chunk_workers} chunk workers"
    )

    def process_wrapper(doc_dir):
        try:
            return process_doc_dir(
                doc_dir,
                base_url,
                api_key,
                args.model,
                min_request_interval,
                max_workers=args.chunk_workers,
            )
        except Exception as e:
            logger.error(f"Failed to process {doc_dir.name}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=args.doc_workers) as executor:
        futures = {executor.submit(process_wrapper, d): d for d in doc_dirs}

        with tqdm(total=len(doc_dirs), desc="Extracting entities") as pbar:
            for future in as_completed(futures):
                doc_dir = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Unexpected error in thread for {doc_dir.name}: {e}")
                finally:
                    pbar.update(1)


if __name__ == "__main__":
    main()
