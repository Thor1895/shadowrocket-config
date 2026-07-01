from __future__ import annotations

from pathlib import Path

from core.classifier import ai_fallback_nodes, classify_node_name
from core.constants import AI_SERVICES, NODE_SCORE_FILE, REGION_POLICY_GROUPS, REGION_POLICY_REGEX, URL_TEST_OPTIONS
from core.scorer import load_top_nodes


def _valid_scored_nodes(nodes: list[dict], score_path: Path, limit: int) -> list[str]:
    node_names = {node["name"] for node in nodes}
    return [name for name in load_top_nodes(score_path, limit=limit) if name in node_names]


def _node_region_policy(name: str) -> str | None:
    categories = classify_node_name(name)
    for region in ("japan", "singapore", "united_states", "hong_kong", "macau"):
        if region in categories:
            return REGION_POLICY_GROUPS[region]
    return None


def _policies_for_node_names(node_names: list[str]) -> list[str]:
    policies: list[str] = []
    for name in node_names:
        policy = _node_region_policy(name)
        if policy and policy not in policies:
            policies.append(policy)
    return policies


def ai_nodes(nodes: list[dict], score_path: Path = NODE_SCORE_FILE, limit: int = 3) -> list[str]:
    scored = _policies_for_node_names(_valid_scored_nodes(nodes, score_path, limit))
    if scored:
        return scored
    return _policies_for_node_names(ai_fallback_nodes(nodes)[:limit])


def route(service: str, nodes: list[dict], score_path: Path = NODE_SCORE_FILE) -> list[str]:
    if service in AI_SERVICES:
        return ai_nodes(nodes, score_path=score_path)
    if service in {"Bank", "China Apps"}:
        return ["DIRECT"]
    if service == "Streaming":
        return ["专线节点", "香港节点", "日本节点", "新加坡节点", "美国节点"]
    if service == "PROXY":
        return ["全部节点", "DIRECT"]
    raise ValueError(f"Unknown service route {service!r}")


def regex_policy_groups() -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "type": "url-test",
            "options": ["use=true", f"policy-regex-filter={regex}", *URL_TEST_OPTIONS[1:]],
            "members": [],
        }
        for name, regex in REGION_POLICY_REGEX.items()
    ]


def build_proxy_groups(nodes: list[dict], score_path: Path = NODE_SCORE_FILE) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = [
        {"name": "PROXY", "type": "select", "members": route("PROXY", nodes, score_path=score_path)},
        {"name": "OpenAI", "type": "select", "members": route("OpenAI", nodes, score_path=score_path)},
        {"name": "Streaming", "type": "select", "members": route("Streaming", nodes, score_path=score_path)},
        {"name": "Gemini", "type": "select", "members": route("Gemini", nodes, score_path=score_path)},
        {"name": "Claude", "type": "select", "members": route("Claude", nodes, score_path=score_path)},
    ]
    groups.extend(regex_policy_groups())
    validate_proxy_groups(groups)
    return groups


def validate_proxy_groups(groups: list[dict[str, object]]) -> None:
    known_policies = {str(group["name"]) for group in groups} | {"DIRECT"}
    for group in groups:
        name = str(group["name"])
        members = list(group.get("members", []))  # type: ignore[arg-type]
        if name in AI_SERVICES and "PROXY" in members:
            raise ValueError(f"{name} group must not include PROXY")
        for member in members:
            if member not in known_policies:
                raise ValueError(f"Unknown policy member {member!r} in {name}")
