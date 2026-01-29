import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse, Response
from app.core.logging import logger
from typing import Awaitable, Callable

# Sensitive headers that should never be logged
SENSITIVE_HEADERS = {
    "authorization", "cookie", "set-cookie", "x-api-key",
    "x-auth-token", "x-csrf-token", "x-xsrf-token"
}

# Sensitive body fields that should be redacted
SENSITIVE_FIELDS = {
    "password", "passwd", "secret", "token", "apikey", "api_key",
    "access_token", "refresh_token", "private_key", "credential"
}


def _sanitize_headers(headers: dict) -> dict:
    """Remove sensitive headers from logs."""
    return {
        k: "***REDACTED***" if k.lower() in SENSITIVE_HEADERS else v
        for k, v in headers.items()
    }


def _sanitize_body(body: dict) -> dict:
    """Redact sensitive fields from request/response bodies."""
    if not isinstance(body, dict):
        return body

    sanitized = {}
    for key, value in body.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_body(value)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_body(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        # Log request with sanitized headers
        safe_headers = _sanitize_headers(dict(request.headers))
        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Headers: {json.dumps(safe_headers, default=str)}"
        )

        # Get original response
        response = await call_next(request)

        # Log response status (no headers or body to avoid PII exposure)
        logger.info(f"Response status: {response.status_code}")

        # For streaming responses, don't log body content
        is_streaming = isinstance(response, StreamingResponse)
        is_sse = "text/event-stream" in response.media_type

        if is_streaming and is_sse:
            async def logging_wrapper():
                try:
                    async for chunk in response.body_iterator:
                        yield chunk
                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    raise

            return StreamingResponse(
                content=logging_wrapper(),
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        else:
            # Non-streaming: pass through without logging body content
            response_body = []
            async for chunk in response.body_iterator:
                response_body.append(chunk)

            response_body_bytes = b"".join(response_body)

            return Response(
                content=response_body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )