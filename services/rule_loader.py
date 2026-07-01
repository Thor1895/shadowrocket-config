from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.constants import NODES_FILE, RULES_FILE, SETTINGS_FILE


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_nodes(path: Path = NODES_FILE) -> list[dict[str, Any]]:
    return load_yaml(path)["nodes"]


def load_rules(path: Path = RULES_FILE) -> list[dict[str, Any]]:
    return load_yaml(path)["rules"]


def load_settings(path: Path = SETTINGS_FILE) -> dict[str, Any]:
    return load_yaml(path)


def load_build_inputs() -> dict[str, Any]:
    return {
        "settings": load_settings(),
        "nodes": load_nodes(),
        "rules": load_rules(),
    }
