from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.classify_nodes import classify_node_name, load_nodes


HEALTH_JSON = ROOT / "output" / "openai_health.json"
HEALTH_MD = ROOT / "output" / "openai_health.md"
OPENAI_REGIONS = {"japan", "singapore", "united_states"}
CHATGPT_TRACE_URL = "https://chatgpt.com/cdn-cgi/trace"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
DEFAULT_TIMEOUT_SECONDS = 8.0


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
    if "direct" in categories and categories & OPENAI_REGIONS:
        return True, "mock: direct JP/SG/US candidate"
    return False, "mock: not a direct JP/SG/US candidate"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_url(url: str, timeout: float, headers: dict[str, str] | None = None) -> tuple[bool, int | None, str | None]:
    request = Request(url, headers=headers or {"User-Agent": "shadowrocket-config-openai-check/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            response.read(256)
        return 200 <= status < 400, status, None
    except HTTPError as exc:
        return False, exc.code, f"HTTP {exc.code}: {exc.reason}"
    except URLError as exc:
        return False, None, str(exc.reason)
    except TimeoutError:
        return False, None, "request timed out"
    except OSError as exc:
        return False, None, str(exc)


def real_check_node(name: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    started = time.monotonic()
    errors: list[str] = []

    chatgpt_reachable, _, chatgpt_error = request_url(CHATGPT_TRACE_URL, timeout=timeout)
    if chatgpt_error:
        errors.append(f"chatgpt.com: {chatgpt_error}")

    api_reachable: bool | None = None
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "shadowrocket-config-openai-check/1.0",
        }
        api_reachable, _, api_error = request_url(OPENAI_MODELS_URL, timeout=timeout, headers=headers)
        if api_error:
            errors.append(f"api.openai.com: {api_error}")

    latency_ms = round((time.monotonic() - started) * 1000)
    openai_available = chatgpt_reachable if api_reachable is None else chatgpt_reachable and api_reachable
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
        "latency_ms": latency_ms,
    }


def mock_result_for_node(name: str, checked_at: str) -> dict[str, Any]:
    available, reason = mock_check_node(name)
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


def _format_optional_bool(value: Any) -> str:
    if value is None:
        return "-"
    return "true" if value else "false"


def write_health_files(
    input_path: Path | None = None,
    json_path: Path = HEALTH_JSON,
    md_path: Path = HEALTH_MD,
    mode: str = "mock",
) -> tuple[Path, Path]:
    names = load_candidate_names(input_path)
    results = check_nodes(names, mode=mode)
    if input_path and input_path.is_relative_to(ROOT):
        source = str(input_path.relative_to(ROOT))
    else:
        source = str(input_path or "config/nodes.yaml")

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


if __name__ == "__main__":
    raise SystemExit(main())
