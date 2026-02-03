"""Structured JSON logging with rotation and correlation ID support."""

import logging
import os
import sys
import threading
import uuid
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from typing import Any

from pythonjsonlogger import jsonlogger

from .config import settings

# Context variable for request correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())[:8]
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(cid)


class CorrelationIdFilter(logging.Filter):
    """Filter that adds correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["correlation_id"] = getattr(record, "correlation_id", "")
        log_record["thread"] = threading.current_thread().name
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


def setup_logging() -> logging.Logger:
    """Configure structured JSON logging with rotation."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # JSON format with key fields
    json_format = "%(timestamp)s %(level)s %(name)s %(correlation_id)s %(message)s"
    json_formatter = CustomJsonFormatter(json_format)

    # Correlation ID filter
    correlation_filter = CorrelationIdFilter()

    # Stdout handler (for container logs / console)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(json_formatter)
    stdout_handler.addFilter(correlation_filter)
    root_logger.addHandler(stdout_handler)

    # File handler with rotation (50MB max, 3 backups)
    # Gracefully skip file logging if directory is not writable
    log_file = settings.log_file
    try:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(correlation_filter)
        root_logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        # Log to stderr if file logging fails (stdout handler already added)
        root_logger.warning(f"File logging disabled: {e}")

    return root_logger


# Initialize logging on module import
_root_logger = setup_logging()

# Application logger
logger = logging.getLogger(__name__)
