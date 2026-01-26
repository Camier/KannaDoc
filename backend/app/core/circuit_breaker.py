"""
Circuit breaker pattern for external service calls.
Prevents cascading failures when external services are unavailable.
"""
import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Optional
from circuitbreaker import circuit, CircuitBreakerError

from app.core.logging import logger


class CircuitBreakerConfig:
    """Configuration for circuit breakers."""

    # Default thresholds
    DEFAULT_FAILURE_THRESHOLD = 5
    DEFAULT_RECOVERY_TIMEOUT = 60  # seconds
    DEFAULT_EXPECTED_EXCEPTION = Exception

    # Service-specific configs
    EMBEDDING_SERVICE = {
        "failure_threshold": 5,
        "recovery_timeout": 60,
        "expected_exception": Exception,
    }

    LLM_SERVICE = {
        "failure_threshold": 5,
        "recovery_timeout": 60,
        "expected_exception": Exception,
    }

    # Provider-specific LLM configs with different timeouts
    DEEPSEEK_REASONER = {
        "failure_threshold": 3,  # More conservative for expensive reasoning models
        "recovery_timeout": 300,  # 5 minutes for deepseek-r1
        "expected_exception": Exception,
    }

    ZHIPU_LLM = {
        "failure_threshold": 5,
        "recovery_timeout": 180,  # 3 minutes for GLM models
        "expected_exception": Exception,
    }

    VECTOR_DB_SERVICE = {
        "failure_threshold": 3,
        "recovery_timeout": 30,
        "expected_exception": Exception,
    }

    MONGODB_SERVICE = {
        "failure_threshold": 5,
        "recovery_timeout": 45,
        "expected_exception": Exception,
    }


def create_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: Optional[type] = None,
):
    """
    Create a circuit breaker decorator.

    Args:
        name: Circuit breaker name for logging
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type that triggers failure

    Returns:
        Circuit breaker decorator
    """

    def decorator(func: Callable) -> Callable:
        # Create the circuit breaker
        cb = circuit(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception or Exception,
            name=name,
        )(func)

        @wraps(cb)
        async def async_wrapper(*args, **kwargs) -> Any:
            """Wrapper for async functions."""
            try:
                return await cb(*args, **kwargs)
            except CircuitBreakerError as e:
                logger.error(
                    f"Circuit breaker '{name}' is OPEN - rejecting request. "
                    f"Service unavailable. Error: {e}"
                )
                raise Exception(
                    f"Service temporarily unavailable due to repeated failures. "
                    f"Please try again later."
                ) from e
            except Exception as e:
                logger.error(f"Circuit breaker '{name}' captured exception: {e}")
                raise

        @wraps(cb)
        def sync_wrapper(*args, **kwargs) -> Any:
            """Wrapper for sync functions."""
            try:
                return cb(*args, **kwargs)
            except CircuitBreakerError as e:
                logger.error(
                    f"Circuit breaker '{name}' is OPEN - rejecting request. "
                    f"Service unavailable. Error: {e}"
                )
                raise Exception(
                    f"Service temporarily unavailable due to repeated failures. "
                    f"Please try again later."
                ) from e
            except Exception as e:
                logger.error(f"Circuit breaker '{name}' captured exception: {e}")
                raise

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Pre-configured circuit breakers for common services

def embedding_service_circuit(func: Callable) -> Callable:
    """Circuit breaker for embedding service calls."""
    config = CircuitBreakerConfig.EMBEDDING_SERVICE
    return create_circuit_breaker(
        name="embedding_service",
        failure_threshold=config["failure_threshold"],
        recovery_timeout=config["recovery_timeout"],
        expected_exception=config["expected_exception"],
    )(func)


def llm_service_circuit(func: Callable) -> Callable:
    """Circuit breaker for LLM service calls."""
    config = CircuitBreakerConfig.LLM_SERVICE
    return create_circuit_breaker(
        name="llm_service",
        failure_threshold=config["failure_threshold"],
        recovery_timeout=config["recovery_timeout"],
        expected_exception=config["expected_exception"],
    )(func)


def vector_db_circuit(func: Callable) -> Callable:
    """Circuit breaker for vector database calls."""
    config = CircuitBreakerConfig.VECTOR_DB_SERVICE
    return create_circuit_breaker(
        name="vector_db",
        failure_threshold=config["failure_threshold"],
        recovery_timeout=config["recovery_timeout"],
        expected_exception=config["expected_exception"],
    )(func)


def mongodb_circuit(func: Callable) -> Callable:
    """Circuit breaker for MongoDB calls."""
    config = CircuitBreakerConfig.MONGODB_SERVICE
    return create_circuit_breaker(
        name="mongodb",
        failure_threshold=config["failure_threshold"],
        recovery_timeout=config["recovery_timeout"],
        expected_exception=config["expected_exception"],
    )(func)


class CircuitBreakerManager:
    """
    Manager for circuit breaker state monitoring and control.
    """

    @staticmethod
    def get_circuit_state(name: str) -> str:
        """Get current state of a circuit breaker."""
        # This would need to access the circuit breaker registry
        # For now, return a placeholder
        return "unknown"

    @staticmethod
    def reset_circuit(name: str):
        """Force reset a circuit breaker to closed state."""
        # This would need to access the circuit breaker registry
        logger.warning(f"Manual reset requested for circuit breaker: {name}")
        pass

    @staticmethod
    def open_circuit(name: str):
        """Force open a circuit breaker."""
        logger.warning(f"Manual open requested for circuit breaker: {name}")
        pass


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()


# Provider-specific circuit breakers for LLM services
def deepseek_reasoner_circuit(func: Callable) -> Callable:
    """Circuit breaker for DeepSeek reasoning models with longer timeout."""
    config = CircuitBreakerConfig.DEEPSEEK_REASONER
    return create_circuit_breaker(
        name="deepseek_reasoner",
        failure_threshold=config["failure_threshold"],
        recovery_timeout=config["recovery_timeout"],
        expected_exception=config["expected_exception"],
    )(func)


def zhipu_llm_circuit(func: Callable) -> Callable:
    """Circuit breaker for Zhipu GLM models with moderate timeout."""
    config = CircuitBreakerConfig.ZHIPU_LLM
    return create_circuit_breaker(
        name="zhipu_llm",
        failure_threshold=config["failure_threshold"],
        recovery_timeout=config["recovery_timeout"],
        expected_exception=config["expected_exception"],
    )(func)
