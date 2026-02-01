"""
Query generator for evaluation datasets.

Generates diverse evaluation queries from a knowledge base corpus.
Uses LLM to create questions from document metadata (titles, filenames).
"""

import asyncio
import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.core.logging import logger
from motor.motor_asyncio import AsyncIOMotorClient


async def generate_queries_from_corpus(kb_id: str, count: int = 50) -> List[str]:
    """
    Generate evaluation queries from knowledge base documents.

    Strategy:
    1. Fetch document metadata from MongoDB (filenames, titles)
    2. Sample documents evenly across corpus
    3. Use LLM to generate diverse questions about each document
    4. Target different question types (factual, comparative, analytical)

    Args:
        kb_id: Knowledge base ID to generate queries from
        count: Target number of queries to generate

    Returns:
        List of query strings
    """
    logger.info(f"Generating {count} queries from kb_id={kb_id}")

    client = AsyncIOMotorClient(
        f"mongodb://{settings.mongodb_root_username}:{settings.mongodb_root_password}@{settings.mongodb_url}/"
    )
    db = client[settings.mongodb_db]

    try:
        files = await db.files.find(
            {
                "knowledge_db_id": kb_id,
                "$or": [{"is_delete": False}, {"is_delete": {"$exists": False}}],
            },
            {"filename": 1, "file_id": 1},
        ).to_list(length=500)

        if not files:
            logger.warning(f"No files found for kb_id={kb_id}")
            return []

        logger.info(f"Found {len(files)} documents in knowledge base")

        docs_needed = min(count, len(files))
        queries_per_doc = count // docs_needed if docs_needed > 0 else 1
        remainder = count % docs_needed if docs_needed > 0 else 0

        all_queries = []

        for idx in range(docs_needed):
            filename = files[idx].get("filename", "Unknown")

            num_queries = queries_per_doc + (1 if idx < remainder else 0)

            doc_queries = await _generate_queries_for_document(
                filename=filename, count=num_queries
            )
            all_queries.extend(doc_queries)

            if idx < docs_needed - 1:
                await asyncio.sleep(10.0)

        logger.info(f"Generated {len(all_queries)} total queries")
        return all_queries[:count]

    finally:
        client.close()


async def _generate_queries_for_document(filename: str, count: int = 3) -> List[str]:
    """
    Generate diverse questions for a specific document.

    Uses LLM to create questions based on document filename/title.
    Requests different question types for diversity.

    Args:
        filename: Document filename (often contains title/topic info)
        count: Number of questions to generate

    Returns:
        List of generated query strings
    """
    title = _extract_title_from_filename(filename)

    prompt = f"""Generate {count} diverse research questions about this academic document:

Title/Topic: {title}

Generate questions that:
1. Ask about specific findings or conclusions
2. Request comparisons or relationships
3. Inquire about methods or approaches
4. Explore implications or applications

Return ONLY the questions, one per line, without numbering or bullets."""

    max_retries = 5
    for attempt in range(max_retries):
        try:
            from app.core.llm.chat_service import ChatService

            class MockMessage:
                def __init__(self, content):
                    self.user_message = content
                    self.conversation_id = "eval_query_gen"
                    self.parent_id = None
                    self.temp_db_id = ""

            llm_config = {
                "model_name": "gemini-3-flash",
                "model_url": "",
                "api_key": "",
                "base_used": [],
                "temperature": 0.8,
                "max_length": 300,
                "top_P": -1,
                "top_K": -1,
                "score_threshold": -1,
            }

            response_chunks = []
            async for chunk in ChatService.create_chat_stream(
                user_message_content=MockMessage(prompt),
                model_config=llm_config,
                message_id=f"query_gen_{hash(title)}_{attempt}",
                system_prompt="",
                is_workflow=True,
            ):
                import json

                try:
                    data = json.loads(chunk)
                    if data.get("type") == "text":
                        response_chunks.append(data.get("data", ""))
                except json.JSONDecodeError:
                    continue

            generated_text = "".join(response_chunks).strip()

            if "LLM_Error" in generated_text or "Error occurred" in generated_text:
                raise ValueError(f"LLM returned error: {generated_text[:100]}")

            queries = [
                q.strip()
                for q in generated_text.split("\n")
                if q.strip() and len(q.strip()) > 10 and not q.strip().startswith("⚠️")
            ]

            if not queries:
                raise ValueError("No queries generated")

            logger.info(f"Generated {len(queries)} queries for: {title[:50]}...")
            return queries[:count]

        except Exception as e:
            logger.warning(
                f"Query generation attempt {attempt + 1} failed for {title[:30]}: {str(e)}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(10 * (attempt + 1))
            else:
                logger.error(f"All query generation attempts failed for {title[:30]}")
                return _fallback_generate_queries(title, count)


def _extract_title_from_filename(filename: str) -> str:
    """
    Extract meaningful title/topic from filename.

    Handles common academic filename patterns:
    - "YYYY - Author - Title.pdf"
    - "Author_YYYY_Title.pdf"
    - "Title (YYYY).pdf"

    Args:
        filename: Original filename

    Returns:
        Extracted title or filename if parsing fails
    """
    name = filename.rsplit(".", 1)[0]

    if " - " in name:
        parts = name.split(" - ")
        if len(parts) >= 3:
            return " - ".join(parts[2:])
        elif len(parts) == 2:
            return parts[1]

    if "_" in name:
        parts = name.split("_")
        if len(parts) >= 3:
            return " ".join(parts[2:])

    return name


def _fallback_generate_queries(title: str, count: int) -> List[str]:
    """
    Generate basic fallback queries when LLM is unavailable.

    Uses simple templates based on document title.

    Args:
        title: Document title/topic
        count: Number of queries to generate

    Returns:
        List of template-based queries
    """
    templates = [
        f"What are the main findings in {title}?",
        f"What methods are used in {title}?",
        f"What are the key conclusions of {title}?",
        f"How does {title} relate to existing research?",
        f"What are the limitations discussed in {title}?",
        f"What future work is suggested in {title}?",
    ]

    return templates[:count]
