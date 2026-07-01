from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
NODES_FILE = ROOT / "config" / "nodes.yaml"
REPORT_FILE = ROOT / "output" / "node_groups_report.md"

TYPE_ALIASES = {
    "direct": ("direct", "直连"),
    "relay": ("relay", "中转", "transit"),
    "dedicated": ("dedicated", "iplc", "iepl", "premium", "专线"),
}

REGION_ALIASES = {
    "hong_kong": ("hk", "hongkong", "hong kong", "香港"),
    "macau": ("mo", "macau", "macao", "澳门"),
    "japan": ("jp", "japan", "tokyo", "osaka", "日本", "东京", "大阪"),
    "singapore": ("sg", "singapore", "新加坡"),
    "united_states": ("us", "usa", "united states", "america", "losangeles", "los angeles", "美国", "洛杉矶"),
}


def load_nodes(path: Path = NODES_FILE) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data["nodes"]


def _contains_alias(normalized_name: str, alias: str) -> bool:
    normalized_alias = alias.lower().replace("-", " ")
    if len(normalized_alias) <= 3 and normalized_alias.isascii():
        return normalized_alias in normalized_name.split()
    return normalized_alias in normalized_name


def _matches_alias(normalized_name: str, compact_name: str, alias: str) -> bool:
    compact_alias = alias.lower().replace(" ", "")
    if _contains_alias(normalized_name, alias):
        return True
    return len(compact_alias) > 3 and compact_alias in compact_name


def classify_node_name(name: str) -> set[str]:
    normalized = name.lower().replace("_", " ").replace("-", " ")
    compact = normalized.replace(" ", "")
    categories: set[str] = set()

    for category, aliases in TYPE_ALIASES.items():
        if any(_matches_alias(normalized, compact, alias) for alias in aliases):
            categories.add(category)

    for region, aliases in REGION_ALIASES.items():
        if any(_matches_alias(normalized, compact, alias) for alias in aliases):
            categories.add(region)

    return categories


def classify_nodes(nodes: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups = {key: [] for key in [*TYPE_ALIASES.keys(), *REGION_ALIASES.keys(), "unclassified"]}
    for node in nodes:
        name = node["name"]
        categories = classify_node_name(name)
        if not categories:
            groups["unclassified"].append(name)
            continue
        for category in categories:
            groups[category].append(name)
    return groups


def names_with_categories(nodes: list[dict[str, Any]], required: set[str]) -> list[str]:
    return [
        node["name"]
        for node in nodes
        if required.issubset(classify_node_name(node["name"]))
    ]


def openai_default_nodes(nodes: list[dict[str, Any]]) -> list[str]:
    allowed_regions = {"japan", "singapore", "united_states"}
    return [
        node["name"]
        for node in nodes
        if "direct" in classify_node_name(node["name"])
        and classify_node_name(node["name"]) & allowed_regions
    ]


def streaming_nodes(nodes: list[dict[str, Any]]) -> list[str]:
    dedicated = names_with_categories(nodes, {"dedicated"})
    all_names = [node["name"] for node in nodes]
    return dedicated + [name for name in all_names if name not in dedicated]


def render_report(nodes: list[dict[str, Any]]) -> str:
    groups = classify_nodes(nodes)
    lines = [
        "# Node Groups Report",
        "",
        "Generated from `config/nodes.yaml` by `scripts/classify_nodes.py`.",
        "",
    ]
    labels = {
        "direct": "Direct / 直连",
        "relay": "Relay / 中转",
        "dedicated": "Dedicated / 专线",
        "hong_kong": "Hong Kong / 香港",
        "macau": "Macau / 澳门",
        "japan": "Japan / 日本",
        "singapore": "Singapore / 新加坡",
        "united_states": "United States / 美国",
        "unclassified": "Unclassified",
    }
    for key, label in labels.items():
        lines.append(f"## {label}")
        members = groups[key]
        if members:
            lines.extend(f"- {member}" for member in members)
        else:
            lines.append("- None")
        lines.append("")
    return "\n".join(lines)


def write_report(path: Path = REPORT_FILE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = render_report(load_nodes())
    path.write_text(report, encoding="utf-8")
    return path


def main() -> int:
    path = write_report()
    print(f"Generated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
