from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build
from scripts import node_scorer
from scripts.classify_nodes import load_nodes


def test_scoring_output_is_stable_for_mock_health() -> None:
    nodes = [
        {"name": "JP-Direct-Tokyo"},
        {"name": "HK-Dedicated-HongKong"},
        {"name": "MO-Relay-Macau"},
    ]
    health = {
        "JP-Direct-Tokyo": {"openai": True, "latency_ms": 80, "tls_connect_success": True, "packet_loss": 0.02},
        "HK-Dedicated-HongKong": {"openai": False, "latency_ms": 45, "tls_connect_success": True, "packet_loss": 0.05},
        "MO-Relay-Macau": {"openai": False, "latency_ms": 60, "tls_connect_success": True, "packet_loss": 0.06},
    }

    scored = node_scorer.score_nodes(nodes, health)

    assert scored[0]["name"] == "JP-Direct-Tokyo"
    assert scored[0]["score"] == 86.8
    assert scored[0]["openai_success_rate"] == 1.0
    assert scored[1]["name"] == "HK-Dedicated-HongKong"
    assert scored[1]["region_penalty"] == 20
    assert scored[2]["name"] == "MO-Relay-Macau"


def test_top3_selection_uses_score_order(tmp_path: Path) -> None:
    score_file = tmp_path / "node_score.json"
    score_file.write_text(
        json.dumps(
            {
                "results": [
                    {"name": "slow", "score": 50, "latency_ms": 300},
                    {"name": "fast", "score": 99, "latency_ms": 20},
                    {"name": "steady", "score": 90, "latency_ms": 60},
                    {"name": "backup", "score": 75, "latency_ms": 80},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert node_scorer.load_top_nodes(score_file, limit=3) == ["fast", "steady", "backup"]


def test_write_scores_outputs_top_nodes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(node_scorer, "now_iso", lambda: "2026-07-01T00:00:00+00:00")
    output = tmp_path / "node_score.json"

    node_scorer.write_scores(output_path=output, health_path=Path("/missing/openai_health.json"))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["generated_at"] == "2026-07-01T00:00:00+00:00"
    assert payload["top_nodes"] == ["JP-Direct-Tokyo", "SG-Direct-Singapore", "US-Direct-LosAngeles"]
    assert payload["results"][0]["score"] >= payload["results"][1]["score"]


def test_build_ai_selection_falls_back_without_score_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(build, "NODE_SCORE_FILE", tmp_path / "missing_node_score.json")

    assert build.select_ai_nodes(load_nodes()) == [
        "JP-Direct-Tokyo",
        "SG-Direct-Singapore",
        "US-Direct-LosAngeles",
    ]
