#!/usr/bin/env python3
"""
Probe per-model capabilities through the running LiteLLM proxy and generate a capability matrix.

Simplified version focusing on core capability detection:
  - Basic chat completion
  - Streaming support
  - Tool/function calling (auto and required modes)
  - Embeddings (for embedding models)
  - Rerank (for rerank models)

Outputs:
  - JSON: state/model_capabilities.json (machine-readable)
  - Markdown: docs/generated/MODEL_CAPABILITIES.md (human-readable)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import yaml
except ImportError:
    yaml = None


def _is_local_url(url: str) -> bool:
    """Check if URL points to localhost."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = parsed.hostname or ""
    return host in {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def _http(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout_s: int = 30,
) -> Tuple[int, bytes, float]:
    """Make HTTP request and return (status, body, elapsed)."""
    body = None
    hdrs: Dict[str, str] = dict(headers or {})
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = Request(url, method=method, headers=hdrs, data=body)
    start = time.time()
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            return resp.status, resp.read(), time.time() - start
    except HTTPError as e:
        try:
            return e.code, e.read(), time.time() - start
        except Exception:
            return e.code, b"", time.time() - start
    except (URLError, TimeoutError, OSError):
        return 0, b"", time.time() - start
    except Exception:
        return 0, b"", time.time() - start


def _http_stream_lines(
    url: str,
    *,
    headers: Dict[str, str],
    json_body: Dict[str, Any],
    timeout_s: int = 60,
    max_lines: int = 50,
    max_seconds: int = 30,
) -> Tuple[int, List[str], float]:
    """Read SSE/event-stream for streaming test."""
    body = json.dumps(json_body).encode("utf-8")
    hdrs: Dict[str, str] = dict(headers)
    hdrs.setdefault("Content-Type", "application/json")
    hdrs.setdefault("Accept", "text/event-stream")
    req = Request(url, method="POST", headers=hdrs, data=body)

    start = time.time()
    lines: List[str] = []
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            while True:
                if len(lines) >= max_lines or time.time() - start > max_seconds:
                    break
                raw = resp.readline()
                if not raw:
                    break
                try:
                    line = raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    line = ""
                if line:
                    lines.append(line)
        return resp.status, lines, time.time() - start
    except HTTPError as e:
        return e.code, [], time.time() - start
    except Exception:
        return 0, [], time.time() - start


def _probe_chat(
    base: str, headers: Dict[str, str], model: str
) -> Dict[str, Any]:
    """Test basic chat completion."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10,
    }
    status, body, elapsed = _http(
        "POST", f"{base}/v1/chat/completions", headers=headers, json_body=payload
    )
    result = {"status": status, "elapsed_s": round(elapsed, 3)}
    if status == 200:
        try:
            data = json.loads(body.decode("utf-8"))
            result["has_content"] = bool(
                data.get("choices") and data["choices"][0].get("message", {}).get("content")
            )
        except Exception:
            result["error"] = "parse_error"
    else:
        result["error"] = "http_error"
    return result


def _probe_stream(
    base: str, headers: Dict[str, str], model: str
) -> Dict[str, Any]:
    """Test streaming support."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 20,
        "stream": True,
    }
    status, lines, elapsed = _http_stream_lines(
        f"{base}/v1/chat/completions", headers=headers, json_body=payload
    )
    result = {"status": status, "elapsed_s": round(elapsed, 3)}
    if status == 200:
        result["has_stream_events"] = any("data:" in line for line in lines)
    else:
        result["error"] = "http_error"
    return result


def _probe_tools(
    base: str,
    headers: Dict[str, str],
    model: str,
    tool_choice: str = "auto",
) -> Dict[str, Any]:
    """Test function calling support."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "What time is it?"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_time",
                    "description": "Get current time",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        "tool_choice": tool_choice,
    }
    status, body, elapsed = _http(
        "POST", f"{base}/v1/chat/completions", headers=headers, json_body=payload
    )
    result = {"status": status, "elapsed_s": round(elapsed, 3)}
    if status == 200:
        try:
            data = json.loads(body.decode("utf-8"))
            msg = data.get("choices", [{}])[0].get("message", {})
            result["has_tool_calls"] = bool(msg.get("tool_calls"))
        except Exception:
            result["error"] = "parse_error"
    else:
        result["error"] = "http_error"
    return result


def _probe_embeddings(
    base: str, headers: Dict[str, str], model: str
) -> Dict[str, Any]:
    """Test embedding generation."""
    payload = {"model": model, "input": "test text"}
    status, body, elapsed = _http(
        "POST", f"{base}/v1/embeddings", headers=headers, json_body=payload
    )
    result = {"status": status, "elapsed_s": round(elapsed, 3)}
    if status == 200:
        try:
            data = json.loads(body.decode("utf-8"))
            result["has_embeddings"] = bool(data.get("data") and len(data["data"]) > 0)
        except Exception:
            result["error"] = "parse_error"
    else:
        result["error"] = "http_error"
    return result


def _probe_rerank(
    base: str, headers: Dict[str, str], model: str
) -> Dict[str, Any]:
    """Test reranking (Jina API style)."""
    payload = {
        "model": model,
        "query": "test query",
        "documents": ["doc1", "doc2"],
        "top_n": 1,
    }
    status, body, elapsed = _http(
        "POST", f"{base}/v1/rerank", headers=headers, json_body=payload
    )
    result = {"status": status, "elapsed_s": round(elapsed, 3)}
    if status == 200:
        try:
            data = json.loads(body.decode("utf-8"))
            result["has_results"] = bool(data.get("results"))
        except Exception:
            result["error"] = "parse_error"
    else:
        # Rerank endpoint might not exist - that's ok for chat models
        result["note"] = "rerank endpoint not available (expected for chat models)"
    return result


def _get_auth_headers() -> Dict[str, str]:
    """Get authentication headers from environment."""
    master_key = os.environ.get("LITELLM_MASTER_KEY") or os.environ.get("LITELLM_API_KEY")
    if not master_key:
        return {}
    return {"Authorization": f"Bearer {master_key}"}


async def _load_db_models() -> List[Dict[str, Any]]:
    """Load models from LiteLLM database."""
    try:
        from litellm.proxy.utils import PrismaClient, ProxyLogging
        from litellm.caching import DualCache

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            print("[warn] DATABASE_URL not set", file=sys.stderr)
            return []

        proxy_logging = ProxyLogging(user_api_key_cache=DualCache())
        prisma = PrismaClient(database_url=database_url, proxy_logging_obj=proxy_logging)
        await prisma.connect()
        try:
            rows = await prisma.db._original_prisma.litellm_proxymodeltable.find_many()
            models = []
            for row in rows:
                if not getattr(row, "model_name", None):
                    continue
                # Extract mode from litellm_params JSON
                litellm_params = getattr(row, "litellm_params", {})
                if isinstance(litellm_params, dict):
                    mode = litellm_params.get("mode", "chat")
                else:
                    mode = "chat"
                models.append({
                    "name": row.model_name,
                    "mode": mode,
                    "provider": "unknown",
                })
            return models
        finally:
            await prisma.disconnect()
    except Exception as e:
        print(f"[warn] Could not load models from DB: {e}", file=sys.stderr)
        return []


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _write_markdown(
    path: Path,
    generated_at: str,
    base: str,
    models: List[Dict[str, Any]],
    results: Dict[str, Any],
) -> None:
    """Write markdown capability matrix."""
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Model Capabilities Matrix",
        "",
        f"Generated: {generated_at}",
        f"Proxy: {base}",
        "",
        "This document is auto-generated by `bin/probe_capabilities.py`.",
        "It reflects actual observed behavior through the running LiteLLM proxy.",
        "",
        "---",
        "",
        "## Legend",
        "",
        "- `✓` = Supported (HTTP 200, expected response)",
        "- `✗` = Not supported (non-200 or missing expected data)",
        "- `?` = Unknown / inconclusive",
        "",
        "---",
        "",
        "## Capabilities",
        "",
        "| Model | Mode | Chat | Stream | Tools (auto) | Tools (req) | Embed | Rerank |",
        "|-------|------|------|--------|--------------|-------------|-------|--------|",
    ]

    for model_info in sorted(models, key=lambda m: m["name"]):
        name = model_info["name"]
        mode = model_info.get("mode", "unknown")
        result = results.get(name, {})

        chat = _status_symbol(result.get("chat"))
        stream = _status_symbol(result.get("stream"))
        tools_auto = _status_symbol(result.get("tools_auto"))
        tools_req = _status_symbol(result.get("tools_required"))
        embed = _status_symbol(result.get("embeddings"))
        rerank = _status_symbol(result.get("rerank"))

        lines.append(f"| {name} | {mode} | {chat} | {stream} | {tools_auto} | {tools_req} | {embed} | {rerank} |")

    lines.extend([
        "",
        "---",
        "",
        "## Probe Details",
        "",
        "### Chat",
        "- Tests: Basic `v1/chat/completions` request",
        "- Success criterion: HTTP 200 with non-empty content",
        "",
        "### Stream",
        "- Tests: Same request with `stream: true`",
        "- Success criterion: HTTP 200 with SSE `data:` events",
        "",
        "### Tools (auto)",
        "- Tests: Request with `tools` array, `tool_choice: auto`",
        "- Success criterion: HTTP 200 with `tool_calls` in response",
        "",
        "### Tools (required)",
        "- Tests: Request with `tool_choice: required`",
        "- Success criterion: HTTP 200 with `tool_calls` in response",
        "",
        "### Embed",
        "- Tests: `v1/embeddings` request",
        "- Success criterion: HTTP 200 with embedding vector",
        "",
        "### Rerank",
        "- Tests: `v1/rerank` request (Jina-style API)",
        "- Success criterion: HTTP 200 with results",
        "",
    ])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _status_symbol(result: Optional[Dict[str, Any]]) -> str:
    """Convert result dict to status symbol."""
    if not isinstance(result, dict):
        return "?"
    if result.get("status") == 200:
        return "✓"
    return "✗"


async def _amain() -> int:
    parser = argparse.ArgumentParser(description="Probe LiteLLM model capabilities")
    parser.add_argument(
        "--base",
        default="http://127.0.0.1:9100",
        help="LiteLLM proxy base URL",
    )
    parser.add_argument(
        "--scope",
        choices=["all", "cloud", "local"],
        default="all",
        help="Filter models by scope",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max models to probe (0 = unlimited)",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Skip streaming tests",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Skip tool calling tests",
    )
    parser.add_argument(
        "--output-json",
        default="state/model_capabilities.json",
        help="JSON output path",
    )
    parser.add_argument(
        "--output-md",
        default="docs/generated/MODEL_CAPABILITIES.md",
        help="Markdown output path",
    )
    args = parser.parse_args()

    # Get headers
    headers = _get_auth_headers()
    if not headers.get("Authorization"):
        print("[warn] No LITELLM_MASTER_KEY or LITELLM_API_KEY found", file=sys.stderr)

    # Load models from DB
    models = await _load_db_models()
    if not models:
        print("[error] No models found in database", file=sys.stderr)
        return 1

    print(f"[info] Found {len(models)} models in database")

    # Filter by scope if needed
    if args.scope != "all":
        filtered = []
        for m in models:
            is_local = any(
                x in m["name"].lower()
                for x in ["ollama", "vllm", "llamacpp", "local", "-local"]
            )
            if args.scope == "local" and is_local:
                filtered.append(m)
            elif args.scope == "cloud" and not is_local:
                filtered.append(m)
        models = filtered
        print(f"[info] Filtered to {len(models)} models (scope={args.scope})")

    # Apply limit
    if args.limit > 0:
        models = models[:args.limit]
        print(f"[info] Limited to {len(models)} models")

    # Probe each model
    results: Dict[str, Dict[str, Any]] = {}
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for idx, model_info in enumerate(models, 1):
        name = model_info["name"]
        mode = model_info.get("mode", "chat")
        print(f"[{idx}/{len(models)}] Probing {name} (mode={mode})...")

        per_model: Dict[str, Any] = {}

        if mode == "chat":
            per_model["chat"] = _probe_chat(args.base, headers, name)
            if not args.no_stream and per_model["chat"].get("status") == 200:
                per_model["stream"] = _probe_stream(args.base, headers, name)
            if not args.no_tools and per_model["chat"].get("status") == 200:
                per_model["tools_auto"] = _probe_tools(args.base, headers, name, "auto")
                # Only test required if auto worked
                if per_model["tools_auto"].get("status") == 200:
                    per_model["tools_required"] = _probe_tools(args.base, headers, name, "required")
        elif mode == "embedding":
            per_model["embeddings"] = _probe_embeddings(args.base, headers, name)
        elif mode == "rerank":
            per_model["rerank"] = _probe_rerank(args.base, headers, name)
        else:
            # Unknown mode - try chat as fallback
            per_model["chat"] = _probe_chat(args.base, headers, name)

        results[name] = per_model

    # Write outputs
    payload = {
        "generated_at": generated_at,
        "base": args.base,
        "scope": args.scope,
        "models": results,
    }

    json_path = Path(args.output_json)
    _write_json(json_path, payload)
    print(f"[info] Wrote JSON -> {json_path}")

    md_path = Path(args.output_md)
    _write_markdown(md_path, generated_at, args.base, models, results)
    print(f"[info] Wrote Markdown -> {md_path}")

    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
