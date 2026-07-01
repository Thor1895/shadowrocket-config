from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
TEMPLATE_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "shadowrocket.conf"


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_config() -> dict[str, Any]:
    nodes_config = load_yaml(CONFIG_DIR / "nodes.yaml")
    rules_config = load_yaml(CONFIG_DIR / "rules.yaml")
    settings = load_yaml(CONFIG_DIR / "settings.yaml")

    nodes = nodes_config["nodes"]
    node_by_name = {node["name"]: node for node in nodes}

    def names_for_countries(countries: set[str]) -> list[str]:
        return [node["name"] for node in nodes if node["country"] in countries]

    openai_nodes = names_for_countries({"JP", "SG", "US"})
    if not openai_nodes:
        raise ValueError("OpenAI group needs at least one JP, SG, or US node")

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
