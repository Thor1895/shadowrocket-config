from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.classify_nodes import classify_node_name, load_nodes


HEALTH_FILE = ROOT / "output" / "openai_health.json"
SCORE_FILE = ROOT / "output" / "node_score.json"

MOCK_LATENCY = {
    "hong_kong": 45,
    "macau": 60,
    "japan": 80,
    "singapore": 90,
    "united_states": 120,
}
MOCK_PACKET_LOSS = {
    "hong_kong": 0.05,
    "macau": 0.06,
    "japan": 0.02,
    "singapore": 0.02,
    "united_states": 0.03,
}
REGION_PENALTIES = {
    "hong_kong": 20,
    "macau": 25,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_health(path: Path = HEALTH_FILE) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    results = payload.get("results", []) if isinstance(payload, dict) else []
    return {
        result["name"]: result
        for result in results
        if isinstance(result, dict) and isinstance(result.get("name"), str)
    }


def _first_category_value(categories: set[str], table: dict[str, float | int], default: float | int) -> float:
    for category in ("hong_kong", "macau", "japan", "singapore", "united_states"):
        if category in categories and category in table:
            return float(table[category])
    return float(default)


def mock_latency_ms(categories: set[str]) -> int:
    return int(_first_category_value(categories, MOCK_LATENCY, 150))


def mock_packet_loss(categories: set[str]) -> float:
    return _first_category_value(categories, MOCK_PACKET_LOSS, 0.08)


def default_success_rate(categories: set[str]) -> float:
    if "direct" in categories and categories & {"japan", "singapore", "united_states"}:
        return 0.82
    if "dedicated" in categories:
        return 0.45
    return 0.35


def health_success_rate(health: dict[str, Any], categories: set[str]) -> float:
    if isinstance(health.get("success_rate"), (int, float)):
        return float(health["success_rate"])
    if health.get("openai") is True:
        return 1.0
    if health.get("openai") is False:
        return 0.0
    return default_success_rate(categories)


def tls_success(health: dict[str, Any], categories: set[str]) -> bool:
    if isinstance(health.get("tls_connect_success"), bool):
        return health["tls_connect_success"]
    if health.get("chatgpt_reachable") is True or health.get("api_reachable") is True:
        return True
    return bool(categories & {"japan", "singapore", "united_states", "hong_kong", "macau"})


def latency_from_health(health: dict[str, Any], categories: set[str]) -> int:
    if isinstance(health.get("latency_ms"), (int, float)):
        return int(health["latency_ms"])
    histogram = health.get("latency_histogram")
    if isinstance(histogram, list) and histogram:
        values = [value for value in histogram if isinstance(value, (int, float))]
        if values:
            return int(sum(values) / len(values))
    return mock_latency_ms(categories)


def region_penalty(categories: set[str]) -> int:
    return int(sum(penalty for region, penalty in REGION_PENALTIES.items() if region in categories))


def score_node(node: dict[str, Any], health: dict[str, Any] | None = None) -> dict[str, Any]:
    name = node["name"]
    health = health or {}
    categories = classify_node_name(name)
    latency_ms = latency_from_health(health, categories)
    success_rate = max(0.0, min(1.0, health_success_rate(health, categories)))
    tls_connect_success = tls_success(health, categories)
    packet_loss = max(0.0, min(1.0, float(health.get("packet_loss", mock_packet_loss(categories)))))
    penalty = region_penalty(categories)

    latency_component = max(0.0, 35.0 - latency_ms / 10.0)
    success_component = success_rate * 35.0
    tls_component = 15.0 if tls_connect_success else 0.0
    packet_component = (1.0 - packet_loss) * 10.0
    score = max(0.0, round(latency_component + success_component + tls_component + packet_component - penalty, 2))

    return {
        "name": name,
        "score": score,
        "categories": sorted(categories),
        "latency_ms": latency_ms,
        "openai_success_rate": round(success_rate, 4),
        "tls_connect_success": tls_connect_success,
        "packet_loss": round(packet_loss, 4),
        "region_penalty": penalty,
    }


def score_nodes(nodes: list[dict[str, Any]], health_by_name: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    health_by_name = health_by_name or {}
    scored = [score_node(node, health_by_name.get(node["name"])) for node in nodes]
    return sorted(scored, key=lambda item: (-item["score"], item["latency_ms"], item["name"]))


def top_nodes(scored_nodes: list[dict[str, Any]], limit: int = 3) -> list[str]:
    return [node["name"] for node in scored_nodes[:limit]]


def write_scores(
    output_path: Path = SCORE_FILE,
    health_path: Path = HEALTH_FILE,
    limit: int = 3,
) -> Path:
    nodes = load_nodes()
    scored = score_nodes(nodes, load_health(health_path))
    if health_path.exists():
        try:
            source = str(health_path.relative_to(ROOT))
        except ValueError:
            source = str(health_path)
    else:
        source = "mock"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": now_iso(),
        "source": source,
        "top_nodes": top_nodes(scored, limit=limit),
        "results": scored,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def load_top_nodes(path: Path = SCORE_FILE, limit: int = 3) -> list[str]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    top = payload.get("top_nodes")
    if isinstance(top, list) and top:
        return [str(name) for name in top[:limit]]

    results = payload.get("results", [])
    if not isinstance(results, list):
        return []
    scored = [item for item in results if isinstance(item, dict) and "name" in item and "score" in item]
    scored.sort(key=lambda item: (-float(item["score"]), int(item.get("latency_ms", 999999)), str(item["name"])))
    return [str(item["name"]) for item in scored[:limit]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score nodes for dynamic AI routing.")
    parser.add_argument("--output", type=Path, default=SCORE_FILE, help="Node score JSON output path.")
    parser.add_argument("--health", type=Path, default=HEALTH_FILE, help="OpenAI health JSON input path.")
    parser.add_argument("--limit", type=int, default=3, help="Number of top nodes to expose.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = write_scores(output_path=args.output, health_path=args.health, limit=args.limit)
    print(f"Generated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
