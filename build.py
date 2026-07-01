from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scripts.classify_nodes import openai_default_nodes, streaming_nodes


ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
TEMPLATE_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "shadowrocket.conf"
OPENAI_HEALTH_FILE = OUTPUT_DIR / "openai_health.json"


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def openai_nodes_from_health(nodes: list[dict[str, Any]], health_path: Path | None = None) -> list[str]:
    health_path = health_path or OPENAI_HEALTH_FILE
    if not health_path.exists():
        return []

    node_names = {node["name"] for node in nodes}
    payload = yaml.safe_load(health_path.read_text(encoding="utf-8"))
    results = payload.get("results", []) if isinstance(payload, dict) else []
    return [
        result["name"]
        for result in results
        if isinstance(result, dict)
        and result.get("openai") is True
        and result.get("name") in node_names
    ]


def select_openai_nodes(nodes: list[dict[str, Any]], health_path: Path | None = None) -> list[str]:
    healthy_nodes = openai_nodes_from_health(nodes, health_path)
    if healthy_nodes:
        return healthy_nodes
    return openai_default_nodes(nodes)


def load_config() -> dict[str, Any]:
    nodes_config = load_yaml(CONFIG_DIR / "nodes.yaml")
    rules_config = load_yaml(CONFIG_DIR / "rules.yaml")
    settings = load_yaml(CONFIG_DIR / "settings.yaml")

    nodes = nodes_config["nodes"]
    node_by_name = {node["name"]: node for node in nodes}

    openai_nodes = select_openai_nodes(nodes)
    if not openai_nodes:
        raise ValueError("OpenAI group needs at least one direct JP, SG, or US node")

    groups = [
        {
            "name": "PROXY",
            "type": "select",
            "members": [node["name"] for node in nodes] + ["DIRECT"],
        },
        {
            "name": "OpenAI",
            "type": "select",
            "members": openai_nodes,
        },
        {
            "name": "Streaming",
            "type": "select",
            "members": streaming_nodes(nodes),
        },
        {
            "name": "Gemini",
            "type": "select",
            "members": [node["name"] for node in nodes],
        },
        {
            "name": "Claude",
            "type": "select",
            "members": [node["name"] for node in nodes],
        },
    ]

    for group in groups:
        if group["name"] in {"OpenAI", "Gemini", "Claude"} and "PROXY" in group["members"]:
            raise ValueError(f"{group['name']} group must not include PROXY")
        for member in group["members"]:
            if member not in node_by_name and member != "DIRECT":
                raise ValueError(f"Unknown policy member {member!r} in {group['name']}")

    return {
        "settings": settings,
        "nodes": nodes,
        "groups": groups,
        "rules": rules_config["rules"],
    }


def render_config(config: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template("shadowrocket.conf.j2")
    return template.render(**config)


def build() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    rendered = render_config(config)
    OUTPUT_FILE.write_text(rendered, encoding="utf-8")
    return OUTPUT_FILE


if __name__ == "__main__":
    path = build()
    print(f"Generated {path.relative_to(ROOT)}")
