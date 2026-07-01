from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ROUTER_FORBIDDEN = {
    "latency_ms",
    "openai_success_rate",
    "tls_connect_success",
    "packet_loss",
    "region_penalty",
    "MOCK_LATENCY",
    "MOCK_PACKET_LOSS",
    "def score_node",
    "def score_nodes",
}

BUILD_FORBIDDEN = {
    '"OpenAI"',
    '"Gemini"',
    '"Claude"',
    '"PROXY"',
    '"Streaming"',
    "load_top_nodes",
    "score_node",
    "score_nodes",
    "ai_fallback_nodes",
    "premium_nodes_first",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fail(message: str) -> int:
    print(f"complexity_check: {message}", file=sys.stderr)
    return 1


def check_router_boundary() -> int:
    text = read(ROOT / "core" / "router.py")
    leaks = sorted(token for token in ROUTER_FORBIDDEN if token in text)
    if leaks:
        return fail(f"router.py contains scoring details: {', '.join(leaks)}")
    return 0


def check_build_boundary() -> int:
    paths = [ROOT / "build.py", ROOT / "jobs" / "build.py"]
    leaks: list[str] = []
    for path in paths:
        text = read(path)
        for token in BUILD_FORBIDDEN:
            if token in text:
                leaks.append(f"{path.relative_to(ROOT)}:{token}")
    if leaks:
        return fail(f"build entry contains routing or scoring logic: {', '.join(sorted(leaks))}")
    return 0


def check_single_rule_set() -> int:
    rule_sets = [
        path
        for path in ROOT.rglob("rules.yaml")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    ]
    if rule_sets != [ROOT / "data" / "rules.yaml"]:
        display = ", ".join(str(path.relative_to(ROOT)) for path in rule_sets)
        return fail(f"expected only data/rules.yaml rule-set, found: {display}")
    return 0


def check_single_scoring_system() -> int:
    production_files = [
        path
        for path in [*ROOT.glob("*.py"), *ROOT.glob("core/*.py"), *ROOT.glob("services/*.py"), *ROOT.glob("jobs/*.py"), *ROOT.glob("scripts/*.py")]
        if path.name != "complexity_check.py"
    ]
    scoring_defs = []
    for path in production_files:
        text = read(path)
        if "def score_node" in text or "def score_nodes" in text:
            scoring_defs.append(path.relative_to(ROOT))
    if scoring_defs != [Path("core/scorer.py")]:
        display = ", ".join(str(path) for path in scoring_defs)
        return fail(f"expected scoring functions only in core/scorer.py, found: {display}")
    return 0


def main() -> int:
    checks = [
        check_router_boundary,
        check_build_boundary,
        check_single_rule_set,
        check_single_scoring_system,
    ]
    for check in checks:
        result = check()
        if result != 0:
            return result
    print("complexity_check: architecture boundaries passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
