from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.classifier import (
    ai_fallback_nodes as openai_default_nodes,
    classify_node_name,
    classify_nodes,
    names_with_categories,
    premium_nodes_first as streaming_nodes,
    render_report,
    write_report,
)
from services.rule_loader import load_nodes


def main() -> int:
    path = write_report()
    print(f"Generated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
