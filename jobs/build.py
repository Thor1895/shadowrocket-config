from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from core.constants import NODE_SCORE_FILE, OUTPUT_DIR, ROOT, SHADOWROCKET_FILE, TEMPLATE_DIR
from core.router import build_proxy_groups
from services.rule_loader import load_build_inputs


def load_config() -> dict:
    config = load_build_inputs()
    config["groups"] = build_proxy_groups(config["nodes"], score_path=NODE_SCORE_FILE)
    return config


def render_config(config: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template("shadowrocket.conf.j2")
    return template.render(**config)


def build(output_file: Path = SHADOWROCKET_FILE) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rendered = render_config(load_config())
    output_file.write_text(rendered, encoding="utf-8")
    return output_file


def run_sync_guard() -> None:
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_guard.py")], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    run_sync_guard()
    path = build()
    print(f"Generated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
