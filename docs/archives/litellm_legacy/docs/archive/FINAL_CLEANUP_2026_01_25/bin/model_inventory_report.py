#!/usr/bin/env python3
"""
Model inventory report (DB vs /v1/models vs aliases).

Usage:
  python bin/model_inventory_report.py

Outputs:
  - state/model_inventory_report.json
  - docs/generated/MODEL_INVENTORY_REPORT.md
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from litellm.caching import DualCache
from litellm.proxy.utils import PrismaClient, ProxyLogging


DEFAULT_BASE_URL = "http://127.0.0.1:4000"
DEFAULT_OUT_JSON = Path("state/model_inventory_report.json")
DEFAULT_OUT_MD = Path("docs/generated/MODEL_INVENTORY_REPORT.md")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    try:
        data = yaml.safe_load(raw) or {}
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _extract_aliases(cfg: Dict[str, Any]) -> List[Dict[str, str]]:
    router = cfg.get("router_settings")
    if not isinstance(router, dict):
        return []
    aliases = router.get("model_group_alias")
    if not isinstance(aliases, dict):
        return []
    out: List[Dict[str, str]] = []
    for alias, target in sorted(aliases.items()):
        if not isinstance(alias, str):
            continue
        if isinstance(target, str):
            out.append({"alias": alias, "target": target})
        else:
            out.append({"alias": alias, "target": str(target)})
    return out


def _fetch_models(base_url: str, *, headers: Optional[Dict[str, str]]) -> Tuple[int, Optional[Dict[str, Any]], Optional[str]]:
    url = base_url.rstrip("/") + "/v1/models"
    req = Request(url, method="GET")
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    try:
        with urlopen(req, timeout=10) as resp:
            status = resp.status
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            return status, payload, None
    except HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, None, body[:200] if body else str(e)
    except URLError as e:
        return 0, None, str(e)
    except Exception as e:
        return 0, None, str(e)


def _extract_model_ids(payload: Optional[Dict[str, Any]]) -> List[str]:
    if not payload or not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        mid = item.get("id") or item.get("model") or item.get("name")
        if isinstance(mid, str):
            out.append(mid)
    return sorted(set(out))


def _summarize_list(items: Sequence[str], *, max_items: int = 40) -> Tuple[List[str], Optional[str]]:
    items = list(items)
    if len(items) <= max_items:
        return items, None
    return items[:max_items], f"... ({len(items) - max_items} more)"


def _write_md(report: Dict[str, Any], *, out_md: Path) -> None:
    db_models = report["db"]["models"]
    api_models = report["api"]["models"]
    aliases = report["aliases"]["items"]
    diffs = report["diffs"]

    lines: List[str] = []
    lines.append("# Model inventory report")
    lines.append("")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")

    lines.append("## Summary")
    lines.append(f"- DB models: {report['db']['count']}")
    lines.append(f"- /v1/models: {report['api']['count']} (status {report['api']['status']})")
    lines.append(f"- Aliases: {report['aliases']['count']}")
    if report["api"].get("error"):
        lines.append(f"- /v1/models error: {report['api']['error']}")
    lines.append("")

    lines.append("## Diffs")
    for key, label in (
        ("db_only", "DB only"),
        ("api_only", "/v1/models only"),
        ("alias_targets_missing_in_api", "Alias targets missing from /v1/models"),
        ("alias_targets_missing_in_db", "Alias targets missing from DB"),
    ):
        items = diffs.get(key, [])
        subset, remainder = _summarize_list(items)
        lines.append(f"- {label}: {len(items)}")
        for item in subset:
            lines.append(f"  - {item}")
        if remainder:
            lines.append(f"  - {remainder}")
    lines.append("")

    lines.append("## Aliases")
    if not aliases:
        lines.append("(none)")
    else:
        for entry in aliases:
            lines.append(f"- {entry['alias']} -> {entry['target']}")
    lines.append("")

    lines.append("## DB models")
    subset, remainder = _summarize_list(db_models)
    for item in subset:
        lines.append(f"- {item}")
    if remainder:
        lines.append(f"- {remainder}")
    lines.append("")

    lines.append("## /v1/models")
    subset, remainder = _summarize_list(api_models)
    for item in subset:
        lines.append(f"- {item}")
    if remainder:
        lines.append(f"- {remainder}")
    lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _fetch_db_models() -> List[str]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return []

    proxy_logging = ProxyLogging(user_api_key_cache=DualCache())
    prisma = PrismaClient(database_url=database_url, proxy_logging_obj=proxy_logging)
    await prisma.connect()
    try:
        rows = await prisma.db._original_prisma.litellm_proxymodeltable.find_many()
        names = [row.model_name for row in rows if getattr(row, "model_name", None)]
        return sorted(set(names))
    finally:
        await prisma.disconnect()


def main() -> int:
    base_url = os.environ.get("LITELLM_PROXY_URL", DEFAULT_BASE_URL)
    out_json = Path(os.environ.get("MODEL_INVENTORY_JSON", str(DEFAULT_OUT_JSON)))
    out_md = Path(os.environ.get("MODEL_INVENTORY_MD", str(DEFAULT_OUT_MD)))

    headers: Dict[str, str] = {}
    master_key = os.environ.get("LITELLM_MASTER_KEY")
    client_key = os.environ.get("LITELLM_API_KEY")
    if master_key:
        headers["Authorization"] = f"Bearer {master_key}"
    elif client_key:
        headers["Authorization"] = f"Bearer {client_key}"

    status, payload, error = _fetch_models(base_url, headers=headers or None)
    api_models = _extract_model_ids(payload)

    cfg = _load_yaml(Path("config.yaml"))
    aliases = _extract_aliases(cfg)
    alias_targets = sorted({a["target"] for a in aliases})

    db_models = asyncio.run(_fetch_db_models())

    db_set = set(db_models)
    api_set = set(api_models)
    alias_set = set(alias_targets)

    report: Dict[str, Any] = {
        "generated_at": _now_iso(),
        "base_url": base_url,
        "db": {"count": len(db_models), "models": db_models},
        "api": {"count": len(api_models), "models": api_models, "status": status, "error": error},
        "aliases": {"count": len(aliases), "items": aliases},
        "diffs": {
            "db_only": sorted(db_set - api_set),
            "api_only": sorted(api_set - db_set),
            "alias_targets_missing_in_api": sorted(alias_set - api_set),
            "alias_targets_missing_in_db": sorted(alias_set - db_set),
        },
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _write_md(report, out_md=out_md)

    print(f"[ok] wrote {out_json}")
    print(f"[ok] wrote {out_md}")
    if status != 200:
        print(f"[warn] /v1/models status={status}")
        if error:
            print(f"[warn] /v1/models error={error}")
    if not os.environ.get("DATABASE_URL"):
        print("[warn] DATABASE_URL not set; DB model list is empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
