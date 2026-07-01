from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.classify_nodes import classify_node_name, load_nodes


HEALTH_JSON = ROOT / "output" / "openai_health.json"
HEALTH_MD = ROOT / "output" / "openai_health.md"
OPENAI_REGIONS = {"japan", "singapore", "united_states"}


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


def check_nodes(names: list[str], mode: str = "mock") -> list[dict[str, Any]]:
    if mode != "mock":
        raise ValueError("only mock mode is implemented in this phase")

    checked_at = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []
    for name in names:
        available, reason = mock_check_node(name)
        results.append(
            {
                "name": name,
                "categories": sorted(classify_node_name(name)),
                "openai": available,
                "mode": mode,
                "reason": reason,
                "checked_at": checked_at,
            }
        )
    return results


def render_json(results: list[dict[str, Any]], source: str, mode: str) -> str:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
        "| Node | OpenAI | Categories | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for result in results:
        categories = ", ".join(result["categories"]) or "-"
        status = "true" if result["openai"] else "false"
        lines.append(f"| {result['name']} | {status} | {categories} | {result['reason']} |")
    lines.append("")
    return "\n".join(lines)


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
    parser.add_argument("--mode", choices=("mock",), default="mock", help="Detection mode.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    json_path, md_path = write_health_files(input_path=args.input, mode=args.mode)
    print(f"Generated {json_path.relative_to(ROOT)}")
    print(f"Generated {md_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
