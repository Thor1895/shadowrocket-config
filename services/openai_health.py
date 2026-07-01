from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from core.classifier import classify_node_name
from core.constants import AI_FALLBACK_REGIONS, OPENAI_HEALTH_JSON, OPENAI_HEALTH_MD, ROOT
from services.node_health import request_url
from services.rule_loader import load_nodes


CHATGPT_TRACE_URL = "https://chatgpt.com/cdn-cgi/trace"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
DEFAULT_TIMEOUT_SECONDS = 8.0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _node_names_from_markdown_report(path: Path) -> list[str]:
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and stripped != "- None":
            name = stripped[2:].strip()
            if name not in names:
                names.append(name)
    return names


def _node_names_from_structured_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)

    if isinstance(data, dict) and "nodes" in data:
        data = data["nodes"]
    if not isinstance(data, list):
        raise ValueError("node sample list must be a list or an object with a nodes list")

    names: list[str] = []
    for item in data:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and "name" in item:
            names.append(str(item["name"]))
        else:
            raise ValueError("each node sample must be a string or an object with a name field")
    return names


def load_candidate_names(path: Path | None = None) -> list[str]:
    if path is None:
        return [node["name"] for node in load_nodes()]
    if path.suffix.lower() == ".md":
        return _node_names_from_markdown_report(path)
    return _node_names_from_structured_file(path)


def mock_check_node(name: str) -> tuple[bool, str]:
    categories = classify_node_name(name)
    if "direct" in categories and categories & AI_FALLBACK_REGIONS:
        return True, "mock: direct JP/SG/US candidate"
    return False, "mock: not a direct JP/SG/US candidate"


def real_check_node(name: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    started = time.monotonic()
    errors: list[str] = []
    latency_histogram: list[int] = []
    attempted_checks = 1

    chatgpt_started = time.monotonic()
    chatgpt_reachable, _, chatgpt_error = request_url(CHATGPT_TRACE_URL, timeout=timeout)
    latency_histogram.append(round((time.monotonic() - chatgpt_started) * 1000))
    if chatgpt_error:
        errors.append(f"chatgpt.com: {chatgpt_error}")

    api_reachable: bool | None = None
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        attempted_checks += 1
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "shadowrocket-config-openai-check/1.0",
        }
        api_started = time.monotonic()
        api_reachable, _, api_error = request_url(OPENAI_MODELS_URL, timeout=timeout, headers=headers)
        latency_histogram.append(round((time.monotonic() - api_started) * 1000))
        if api_error:
            errors.append(f"api.openai.com: {api_error}")

    latency_ms = round((time.monotonic() - started) * 1000)
    openai_available = chatgpt_reachable if api_reachable is None else chatgpt_reachable and api_reachable
    successful_checks = int(chatgpt_reachable) + (int(api_reachable) if api_reachable is not None else 0)
    return {
        "name": name,
        "categories": sorted(classify_node_name(name)),
        "openai": openai_available,
        "mode": "real",
        "reason": "real: direct access check",
        "checked_at": now_iso(),
        "chatgpt_reachable": chatgpt_reachable,
        "api_reachable": api_reachable,
        "error": "; ".join(errors) if errors else None,
        "success_rate": round(successful_checks / attempted_checks, 4),
        "failure_reasons": errors,
        "latency_histogram": latency_histogram,
        "tls_connect_success": chatgpt_reachable or bool(api_reachable),
        "latency_ms": latency_ms,
    }


def mock_result_for_node(name: str, checked_at: str) -> dict[str, Any]:
    available, reason = mock_check_node(name)
    failure_reasons = [] if available else [reason]
    return {
        "name": name,
        "categories": sorted(classify_node_name(name)),
        "openai": available,
        "mode": "mock",
        "reason": reason,
        "checked_at": checked_at,
        "chatgpt_reachable": available,
        "api_reachable": None,
        "error": None if available else reason,
        "success_rate": 1.0 if available else 0.0,
        "failure_reasons": failure_reasons,
        "latency_histogram": [],
        "tls_connect_success": available,
        "latency_ms": None,
    }


def check_nodes(names: list[str], mode: str = "mock") -> list[dict[str, Any]]:
    if mode not in {"mock", "real"}:
        raise ValueError("mode must be mock or real")

    checked_at = now_iso()
    results: list[dict[str, Any]] = []
    for name in names:
        if mode == "mock":
            results.append(mock_result_for_node(name, checked_at))
        else:
            results.append(real_check_node(name))
    return results


def render_json(results: list[dict[str, Any]], source: str, mode: str) -> str:
    payload = {
        "generated_at": now_iso(),
        "mode": mode,
        "source": source,
        "results": results,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _format_optional_bool(value: Any) -> str:
    if value is None:
        return "-"
    return "true" if value else "false"


def render_markdown(results: list[dict[str, Any]], source: str, mode: str) -> str:
    lines = [
        "# OpenAI Health",
        "",
        f"- Source: `{source}`",
        f"- Mode: `{mode}`",
        "",
        "| Node | OpenAI | ChatGPT | API | Latency ms | Categories | Error |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for result in results:
        categories = ", ".join(result["categories"]) or "-"
        status = "true" if result["openai"] else "false"
        chatgpt = _format_optional_bool(result.get("chatgpt_reachable"))
        api = _format_optional_bool(result.get("api_reachable"))
        latency = result.get("latency_ms")
        latency_text = "-" if latency is None else str(latency)
        error = result.get("error") or "-"
        lines.append(
            f"| {result['name']} | {status} | {chatgpt} | {api} | {latency_text} | {categories} | {error} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_health_files(
    input_path: Path | None = None,
    json_path: Path = OPENAI_HEALTH_JSON,
    md_path: Path = OPENAI_HEALTH_MD,
    mode: str = "mock",
) -> tuple[Path, Path]:
    names = load_candidate_names(input_path)
    results = check_nodes(names, mode=mode)
    if input_path and input_path.is_relative_to(ROOT):
        source = str(input_path.relative_to(ROOT))
    else:
        source = str(input_path or "data/nodes.yaml")

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(render_json(results, source=source, mode=mode), encoding="utf-8")
    md_path.write_text(render_markdown(results, source=source, mode=mode), encoding="utf-8")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check OpenAI availability for candidate nodes.")
    parser.add_argument(
        "--input",
        type=Path,
        help="Optional node sample list or node report. Supports .yaml, .yml, .json, and .md.",
    )
    parser.add_argument("--mode", choices=("mock", "real"), default="mock", help="Detection mode.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    json_path, md_path = write_health_files(input_path=args.input, mode=args.mode)
    print(f"Generated {json_path.relative_to(ROOT)}")
    print(f"Generated {md_path.relative_to(ROOT)}")
    return 0
