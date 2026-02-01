"""
LLM-based relevance labeling for retrieval evaluation.

Uses existing ChatService infrastructure to score query-document pairs
on a 0-3 relevance scale:
- 0: Irrelevant (no useful information)
- 1: Partial (some tangentially related information)
- 2: Relevant (contains useful information)
- 3: Highly relevant (directly answers the query)
"""

import asyncio
import re
from typing import Dict, List, Optional
from app.core.llm.chat_service import ChatService
from app.core.logging import logger


# Prompt template for relevance scoring
RELEVANCE_PROMPT_TEMPLATE = """You are an expert information retrieval evaluator. Your task is to rate how relevant a document is to a given query.

Use this scoring scale:
- 0 (Irrelevant): The document contains no useful information related to the query
- 1 (Partial): The document mentions related concepts but doesn't directly address the query
- 2 (Relevant): The document contains useful information that helps answer the query
- 3 (Highly Relevant): The document directly and comprehensively answers the query

Query: {query}

Document: {document}

Provide ONLY a single integer score (0, 1, 2, or 3) without any explanation."""


async def label_relevance(
    query: str, document: str, llm_config: dict, max_retries: int = 3
) -> int:
    """
    Score the relevance of a document to a query using LLM.

    Args:
        query: Search query string
        document: Document text to evaluate
        llm_config: LLM configuration dict with keys:
            - model_name: str (e.g., 'glm-4-flash')
            - model_url: str (optional, auto-detected if not provided)
            - api_key: str (optional, read from env if not provided)
            - temperature: float (default: 0.0 for consistency)
            - max_length: int (default: 10)
            - top_P: float (default: -1)
            - top_K: int (default: -1)
            - score_threshold: int (default: -1)
        max_retries: Maximum retry attempts for failed LLM calls

    Returns:
        int: Relevance score (0-3)

    Raises:
        ValueError: If LLM returns invalid score format
        RuntimeError: If all retry attempts fail
    """
    prompt = RELEVANCE_PROMPT_TEMPLATE.format(query=query, document=document)

    config = {
        "model_name": llm_config.get("model_name"),
        "model_url": llm_config.get("model_url", ""),
        "api_key": llm_config.get("api_key", ""),
        "base_used": llm_config.get("base_used", []),
        "temperature": llm_config.get("temperature", 0.0),
        "max_length": llm_config.get("max_length", 10),
        "top_P": llm_config.get("top_P", -1),
        "top_K": llm_config.get("top_K", -1),
        "score_threshold": llm_config.get("score_threshold", -1),
    }

    class MockMessage:
        def __init__(self, content):
            self.user_message = content
            self.conversation_id = "eval_labeler"
            self.parent_id = None
            self.temp_db_id = ""

    user_message = MockMessage(prompt)

    # Retry logic with exponential backoff
    for attempt in range(max_retries):
        try:
            response_chunks = []
            async for chunk in ChatService.create_chat_stream(
                user_message_content=user_message,
                model_config=config,
                message_id=f"labeler_{hash(query + document)}",
                system_prompt="",
                history_depth=0,
                save_to_db=False,
                user_image_urls=[],
                supply_info="",
                quote_variables={},
                is_workflow=True,
            ):
                import json

                try:
                    data = json.loads(chunk)
                    if data.get("type") == "text":
                        response_chunks.append(data.get("data", ""))
                except json.JSONDecodeError:
                    continue

            full_response = "".join(response_chunks).strip()
            score = _parse_score(full_response)

            logger.info(
                f"Relevance labeling successful: query='{query[:50]}...', "
                f"score={score}, attempt={attempt + 1}"
            )
            return score

        except Exception as e:
            logger.warning(
                f"LLM labeling failed (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"All {max_retries} retry attempts failed for relevance labeling"
                ) from e
            await asyncio.sleep(2**attempt)

    raise RuntimeError("Unexpected exit from retry loop")


def _parse_score(response: str) -> int:
    """
    Extract numeric score from LLM response.

    Handles various formats:
    - Plain digit: "2"
    - With explanation: "Score: 3"
    - In sentence: "The relevance is 1"

    Args:
        response: Raw LLM response text

    Returns:
        int: Extracted score (0-3)

    Raises:
        ValueError: If no valid score found
    """
    matches = re.findall(r"\b[0-3]\b", response)
    if matches:
        return int(matches[0])

    raise ValueError(
        f"Could not parse valid score (0-3) from LLM response: '{response}'"
    )


async def batch_label_relevance(
    query_doc_pairs: List[tuple[str, str]],
    llm_config: dict,
    max_concurrent: int = 5,
    max_retries: int = 3,
) -> List[int]:
    """
    Score multiple query-document pairs in parallel with concurrency control.

    Args:
        query_doc_pairs: List of (query, document) tuples
        llm_config: LLM configuration (same format as label_relevance)
        max_concurrent: Maximum parallel LLM calls
        max_retries: Retry attempts per call

    Returns:
        List[int]: Relevance scores in same order as input pairs
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _label_with_limit(query: str, document: str) -> int:
        async with semaphore:
            return await label_relevance(query, document, llm_config, max_retries)

    tasks = [_label_with_limit(q, d) for q, d in query_doc_pairs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scores = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(
                f"Failed to label pair {i}: query='{query_doc_pairs[i][0][:50]}...', error={result}"
            )
            scores.append(0)
        else:
            scores.append(result)

    return scores
