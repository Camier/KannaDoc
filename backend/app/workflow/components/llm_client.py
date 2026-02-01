"""
LLM client wrapper with circuit breaker and retry logic.

Wrapper for LLM calls with circuit breaker protection and retry logic
with exponential backoff.
"""

import asyncio
import random
from typing import Optional, Any

from app.core.llm import ChatService
from app.core.circuit_breaker import llm_service_circuit
from app.core.logging import logger
from app.workflow.components.constants import PROVIDER_TIMEOUTS


class LLMClient:
    """
    Wrapper for LLM calls with circuit breaker and retry logic.
    """

    PROVIDER_TIMEOUTS = PROVIDER_TIMEOUTS

    @classmethod
    def get_provider_timeout(cls, model_name: str) -> int:
        """
        Get provider-specific timeout for a model.

        Args:
            model_name: Name of the model

        Returns:
            Timeout in seconds
        """
        model_lower = model_name.lower()
        for provider, timeout in cls.PROVIDER_TIMEOUTS.items():
            if provider == "default":
                continue
            if provider in model_lower:
                return timeout
        return cls.PROVIDER_TIMEOUTS["default"]

    @staticmethod
    async def retry_with_backoff(
        func,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        """
        Execute function with exponential backoff retry.

        Args:
            func: Async function to execute
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries

        Returns:
            Function result

        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                if attempt == max_retries:
                    # All retries exhausted
                    raise

                # Exponential backoff with jitter
                delay = min(base_delay * (2**attempt), max_delay)
                jitter = delay * 0.1  # 10% jitter
                actual_delay = delay + random.uniform(-jitter, jitter)

                logger.warning(
                    f"LLM call failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {actual_delay:.2f}s..."
                )
                await asyncio.sleep(actual_delay)

        if last_exception is not None:
            raise last_exception
        raise RuntimeError("No exception captured but all retries exhausted")

    @llm_service_circuit
    async def call_with_circuit_breaker(
        self,
        user_message_content,
        model_config: dict,
        message_id: str,
        system_prompt: str,
        save_to_db: bool,
        user_image_urls: list,
        supply_info: str = "",
        quote_variables: Optional[dict] = None,
    ):
        """
        LLM call wrapped with circuit breaker protection.

        Args:
            user_message_content: User message content
            model_config: Model configuration
            message_id: Message identifier
            system_prompt: System prompt
            save_to_db: Whether to save to database
            user_image_urls: List of image URLs
            supply_info: Additional supply info
            quote_variables: Variables for quote extraction

        Returns:
            Chat stream generator
        """
        model_name = model_config.get("model_name", "")
        timeout = self.get_provider_timeout(model_name)

        logger.info(
            f"LLM call: model={model_name}, timeout={timeout}s, node={message_id}"
        )

        return ChatService.create_chat_stream(
            user_message_content=user_message_content,
            model_config=model_config,
            message_id=message_id,
            system_prompt=system_prompt,
            save_to_db=save_to_db,
            user_image_urls=user_image_urls,
            supply_info=supply_info,
            quote_variables=quote_variables or {},
        )

    async def call_with_retry(
        self,
        user_message_content,
        model_config: dict,
        message_id: str,
        system_prompt: str,
        save_to_db: bool,
        user_image_urls: list,
        supply_info: str = "",
        quote_variables: Optional[dict] = None,
    ):
        """
        LLM call with both circuit breaker and retry logic.

        Args:
            user_message_content: User message content
            model_config: Model configuration
            message_id: Message identifier
            system_prompt: System prompt
            save_to_db: Whether to save to database
            user_image_urls: List of image URLs
            supply_info: Additional supply info
            quote_variables: Variables for quote extraction

        Returns:
            Chat stream generator
        """
        # Wrap the circuit breaker call in retry logic
        return await self.retry_with_backoff(
            lambda: self.call_with_circuit_breaker(
                user_message_content=user_message_content,
                model_config=model_config,
                message_id=message_id,
                system_prompt=system_prompt,
                save_to_db=save_to_db,
                user_image_urls=user_image_urls,
                supply_info=supply_info,
                quote_variables=quote_variables,
            )
        )
