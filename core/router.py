from __future__ import annotations

from pathlib import Path

from core.classifier import ai_fallback_nodes, premium_nodes_first
from core.constants import AI_SERVICES, NODE_SCORE_FILE
from core.scorer import load_top_nodes


def _valid_scored_nodes(nodes: list[dict], score_path: Path, limit: int) -> list[str]:
    node_names = {node["name"] for node in nodes}
    return [name for name in load_top_nodes(score_path, limit=limit) if name in node_names]


def ai_nodes(nodes: list[dict], score_path: Path = NODE_SCORE_FILE, limit: int = 3) -> list[str]:
    scored = _valid_scored_nodes(nodes, score_path, limit)
    if scored:
        return scored
    return ai_fallback_nodes(nodes)[:limit]


def route(service: str, nodes: list[dict], score_path: Path = NODE_SCORE_FILE) -> list[str]:
    if service in AI_SERVICES:
        return ai_nodes(nodes, score_path=score_path)
    if service in {"Bank", "China Apps"}:
        return ["DIRECT"]
    if service == "Streaming":
        return premium_nodes_first(nodes)
    if service == "PROXY":
        return [node["name"] for node in nodes] + ["DIRECT"]
    raise ValueError(f"Unknown service route {service!r}")


def build_proxy_groups(nodes: list[dict], score_path: Path = NODE_SCORE_FILE) -> list[dict[str, object]]:
    groups = [
        {
            "name": "PROXY",
            "type": "select",
            "members": route("PROXY", nodes, score_path=score_path),
        },
        {
            "name": "OpenAI",
            "type": "select",
            "members": route("OpenAI", nodes, score_path=score_path),
        },
        {
            "name": "Streaming",
            "type": "select",
            "members": route("Streaming", nodes, score_path=score_path),
        },
        {
            "name": "Gemini",
            "type": "select",
            "members": route("Gemini", nodes, score_path=score_path),
        },
        {
            "name": "Claude",
            "type": "select",
            "members": route("Claude", nodes, score_path=score_path),
        },
    ]
    validate_proxy_groups(nodes, groups)
    return groups


def validate_proxy_groups(nodes: list[dict], groups: list[dict[str, object]]) -> None:
    node_by_name = {node["name"]: node for node in nodes}
    for group in groups:
        name = str(group["name"])
        members = list(group["members"])  # type: ignore[arg-type]
        if name in AI_SERVICES and "PROXY" in members:
            raise ValueError(f"{name} group must not include PROXY")
        for member in members:
            if member not in node_by_name and member != "DIRECT":
                raise ValueError(f"Unknown policy member {member!r} in {name}")
