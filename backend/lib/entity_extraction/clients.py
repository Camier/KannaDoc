"""Chat client adapters for entity extraction.

Implements the ChatClient protocol for various LLM providers:
- ZhipuChatClient: Z.ai / Zhipu GLM models
- MinimaxChatClient: MiniMax M2.1 models (fallback)

Usage:
    from lib.entity_extraction.clients import ZhipuChatClient
    from lib.entity_extraction import V31Extractor

    client = ZhipuChatClient(model="glm-4.7-flash")
    extractor = V31Extractor(client=client, model="glm-4.7-flash")
    result = extractor.extract(doc_id="doc1", chunk_id="chunk1", text="...")
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ZhipuChatClient:
    """Chat client for Zhipu GLM models via Z.ai API.

    Uses OpenAI SDK with Z.ai base URL for compatibility.
    Supports structured JSON output via json_schema response format.
    """

    model: str = "glm-4.7-flash"
    base_url: str = "https://api.z.ai/api/coding/paas/v4"
    api_key: Optional[str] = None
    timeout: float = 120.0
    max_retries: int = 3
    _client: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        import openai

        self.api_key = (
            self.api_key
            or os.getenv("ZAI_API_KEY")
            or os.getenv("ZHIPU_API_KEY")
            or os.getenv("ZHIPUAI_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "ZAI_API_KEY, ZHIPU_API_KEY, or ZHIPUAI_API_KEY not found in environment"
            )

        self._client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
        **kwargs: Any,
    ) -> str:
        """Send chat completion request and return response text.

        Parameters:
            messages: List of {role, content} message dicts
            model: Model name (defaults to instance model)
            temperature: Sampling temperature (default 0.7 for GLM-4.7)
            max_tokens: Max response tokens (default 4096)

        Returns:
            Response content as string
        """
        use_model = model or self.model
        delays = [1, 2, 4, 8][: self.max_retries]
        last_error: Optional[Exception] = None

        for attempt, delay in enumerate(delays):
            try:
                response = self._client.chat.completions.create(
                    model=use_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=0.6,
                )
                msg = response.choices[0].message
                content = msg.content or ""

                if not content:
                    raw = msg.model_extra or {}
                    content = raw.get("reasoning_content", "")

                return content.strip()

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if any(x in error_str for x in ["rate", "429", "timeout", "503"]):
                    if attempt < len(delays) - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                        )
                        time.sleep(delay)
                        continue

                logger.error(f"Chat completion failed: {e}")
                break

        raise RuntimeError(f"All retries exhausted: {last_error}")


@dataclass
class MinimaxChatClient:
    """Chat client for MiniMax M2.1 models (fallback provider).

    Uses MiniMax API directly via httpx (not OpenAI SDK, as MiniMax
    uses a different endpoint structure).
    """

    model: str = "abab6.5s-chat"
    base_url: str = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    api_key: Optional[str] = None
    timeout: float = 120.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        import httpx

        self.api_key = self.api_key or os.getenv("MINIMAX_API_KEY")
        if not self.api_key:
            key_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                ".minimax_api_key",
            )
            if os.path.exists(key_file):
                with open(key_file) as f:
                    self.api_key = f.read().strip()

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not found in environment or key file")

        self._http_client = httpx.Client(timeout=self.timeout)

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 4096,
        **kwargs: Any,
    ) -> str:
        """Send chat completion request and return response text."""
        use_model = model or self.model
        delays = [1, 2, 4, 8][: self.max_retries]
        last_error: Optional[Exception] = None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for attempt, delay in enumerate(delays):
            try:
                response = self._http_client.post(
                    self.base_url, json=payload, headers=headers
                )
                if response.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {response.status_code}: {response.text[:500]}"
                    )
                data = response.json()
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                return content.strip()

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if any(x in error_str for x in ["rate", "429", "timeout", "503"]):
                    if attempt < len(delays) - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                        )
                        time.sleep(delay)
                        continue

                logger.error(f"Chat completion failed: {e}")
                break

        raise RuntimeError(f"All retries exhausted: {last_error}")


def get_chat_client(
    provider: str = "zhipu",
    model: Optional[str] = None,
    **kwargs: Any,
) -> ZhipuChatClient | MinimaxChatClient:
    """Factory function to create the appropriate chat client.

    Args:
        provider: "zhipu" or "minimax"
        model: Model name (uses provider default if not specified)
        **kwargs: Additional arguments passed to client constructor

    Returns:
        Configured chat client instance
    """
    if provider == "zhipu":
        return ZhipuChatClient(model=model or "glm-4.7-flash", **kwargs)
    elif provider == "minimax":
        return MinimaxChatClient(model=model or "MiniMax-M2.1", **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'zhipu' or 'minimax'")


__all__ = ["ZhipuChatClient", "MinimaxChatClient", "get_chat_client"]
