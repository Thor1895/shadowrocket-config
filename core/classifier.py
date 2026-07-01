from __future__ import annotations

from pathlib import Path

from core.constants import (
    AI_FALLBACK_REGIONS,
    NODE_GROUPS_REPORT_FILE,
    REGION_ALIASES,
    TYPE_ALIASES,
)
from services.rule_loader import load_nodes


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


def classify_nodes(nodes: list[dict]) -> dict[str, list[str]]:
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


def names_with_categories(nodes: list[dict], required: set[str]) -> list[str]:
    return [
        node["name"]
        for node in nodes
        if required.issubset(classify_node_name(node["name"]))
    ]


def ai_fallback_nodes(nodes: list[dict]) -> list[str]:
    return [
        node["name"]
        for node in nodes
        if "direct" in classify_node_name(node["name"])
        and classify_node_name(node["name"]) & AI_FALLBACK_REGIONS
    ]


def premium_nodes_first(nodes: list[dict]) -> list[str]:
    premium = names_with_categories(nodes, {"dedicated"})
    all_names = [node["name"] for node in nodes]
    return premium + [name for name in all_names if name not in premium]


def render_report(nodes: list[dict]) -> str:
    groups = classify_nodes(nodes)
    lines = [
        "# Node Groups Report",
        "",
        "Generated from `data/nodes.yaml` by `core.classifier`.",
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


def write_report(path: Path = NODE_GROUPS_REPORT_FILE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(load_nodes()), encoding="utf-8")
    return path
