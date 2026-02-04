"""High-performance async DeepSeek client for entity extraction.

Optimized for maximum throughput based on DeepSeek API characteristics:
- NO rate limits: can fire 100s of parallel requests
- Automatic context caching: 90% input cost savings on shared prefixes
- 10-minute timeout tolerance for high-load scenarios

Usage:
    from lib.entity_extraction.deepseek_client import DeepSeekAsyncClient

    async with DeepSeekAsyncClient() as client:
        tasks = [client.chat(messages) for messages in batch]
        results = await asyncio.gather(*tasks)
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 600.0  # 10 minutes - DeepSeek's server timeout
DEFAULT_MAX_CONCURRENT = 50  # Conservative limit for stability
DEFAULT_MODEL = "deepseek-chat"


@dataclass
class DeepSeekAsyncClient:
    """Async client for DeepSeek API with aggressive parallelism.

    DeepSeek has NO rate limits - this client is designed to maximize throughput
    by firing many concurrent requests while maintaining stability.
    """

    model: str = DEFAULT_MODEL
    base_url: str = "https://api.deepseek.com"
    api_key: Optional[str] = None
    timeout: float = DEFAULT_TIMEOUT
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    _client: Any = field(default=None, init=False, repr=False)
    _semaphore: Optional[asyncio.Semaphore] = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment")

    async def __aenter__(self) -> "DeepSeekAsyncClient":
        import openai

        self._client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=3,
        )
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.close()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """Send async chat completion request with concurrency limiting."""
        if self._semaphore is None:
            raise RuntimeError(
                "Client not initialized. Use 'async with' context manager."
            )
        async with self._semaphore:
            try:
                response = await self._client.chat.completions.create(
                    model=model or self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return (response.choices[0].message.content or "").strip()
            except Exception as e:
                logger.error(f"DeepSeek API error: {e}")
                raise

    async def chat_batch(
        self,
        messages_list: List[List[Dict[str, str]]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
        return_exceptions: bool = True,
    ) -> List[str | BaseException]:
        """Process multiple chat requests in parallel.

        Args:
            messages_list: List of message sequences to process
            return_exceptions: If True, exceptions are returned in results
                               If False, first exception is raised

        Returns:
            List of response strings (or exceptions if return_exceptions=True)
        """
        tasks = [
            self.chat(msgs, model=model, temperature=temperature, max_tokens=max_tokens)
            for msgs in messages_list
        ]
        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)


@dataclass
class DeepSeekSyncClient:
    """Synchronous wrapper for backward compatibility with existing code."""

    model: str = DEFAULT_MODEL
    base_url: str = "https://api.deepseek.com"
    api_key: Optional[str] = None
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = 3
    _client: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        import openai

        self.api_key = self.api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment")

        self._client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
        **kwargs: Any,
    ) -> str:
        """Send synchronous chat completion request."""
        response = self._client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()


__all__ = ["DeepSeekAsyncClient", "DeepSeekSyncClient"]
