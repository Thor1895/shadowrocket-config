from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build
from jobs import build as build_job
from services import openai_health as check_openai
from services.openai_health import check_nodes, load_candidate_names, write_health_files
from scripts.validate import parse_groups


def _groups_from_output(path: Path) -> dict[str, list[str]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return parse_groups(lines)


def test_build_prefers_top_nodes_from_score_file(tmp_path: Path, monkeypatch) -> None:
    score_path = tmp_path / "node_score.json"
    score_path.write_text(
        json.dumps(
            {
                "top_nodes": ["HK-Dedicated-HongKong", "MO-Relay-Macau", "JP-Direct-Tokyo"],
                "results": [
                    {"name": "HK-Dedicated-HongKong", "score": 99},
                    {"name": "MO-Relay-Macau", "score": 98},
                    {"name": "JP-Direct-Tokyo", "score": 97},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(build_job, "NODE_SCORE_FILE", score_path)

    output = build.build()
    groups = _groups_from_output(output)

    expected = ["HK-Dedicated-HongKong", "MO-Relay-Macau", "JP-Direct-Tokyo"]
    assert groups["OpenAI"] == expected
    assert groups["Gemini"] == expected
    assert groups["Claude"] == expected


def test_build_falls_back_to_default_ai_candidates_without_score_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(build_job, "NODE_SCORE_FILE", tmp_path / "missing_node_score.json")

    output = build.build()
    groups = _groups_from_output(output)

    assert groups["OpenAI"] == ["JP-Direct-Tokyo", "SG-Direct-Singapore", "US-Direct-LosAngeles"]
    assert groups["Gemini"] == groups["OpenAI"]
    assert groups["Claude"] == groups["OpenAI"]


def test_mock_openai_check_writes_json_and_markdown(tmp_path: Path) -> None:
    sample = tmp_path / "nodes.yaml"
    sample.write_text(
        """
nodes:
  - name: JP-Direct-Tokyo
  - name: HK-Dedicated-HongKong
""".strip(),
        encoding="utf-8",
    )
    json_path = tmp_path / "openai_health.json"
    md_path = tmp_path / "openai_health.md"

    write_health_files(input_path=sample, json_path=json_path, md_path=md_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "mock"
    assert payload["results"][0]["openai"] is True
    assert payload["results"][1]["openai"] is False
    assert "| JP-Direct-Tokyo | true |" in md_path.read_text(encoding="utf-8")
    assert payload["results"][0]["checked_at"]
    assert payload["results"][0]["chatgpt_reachable"] is True
    assert payload["results"][0]["api_reachable"] is None
    assert payload["results"][0]["error"] is None
    assert payload["results"][0]["latency_ms"] is None


def test_openai_check_reads_node_report_markdown(tmp_path: Path) -> None:
    report = tmp_path / "node_groups_report.md"
    report.write_text(
        """
# Node Groups Report

## Direct / 直连
- JP-Direct-Tokyo
- SG-Direct-Singapore

## Unclassified
- None
""".strip(),
        encoding="utf-8",
    )

    assert load_candidate_names(report) == ["JP-Direct-Tokyo", "SG-Direct-Singapore"]


def test_mock_check_nodes_marks_direct_jp_sg_us_as_openai_available() -> None:
    results = check_nodes(["US-Direct-LosAngeles", "MO-Relay-Macau"])

    assert results[0]["openai"] is True
    assert results[1]["openai"] is False


def test_mock_mode_output_is_stable(monkeypatch) -> None:
    monkeypatch.setattr(check_openai, "now_iso", lambda: "2026-07-01T00:00:00+00:00")

    results = check_nodes(["JP-Direct-Tokyo", "HK-Dedicated-HongKong"], mode="mock")

    assert results == [
        {
            "name": "JP-Direct-Tokyo",
            "categories": ["direct", "japan"],
            "openai": True,
            "mode": "mock",
            "reason": "mock: direct JP/SG/US candidate",
            "checked_at": "2026-07-01T00:00:00+00:00",
            "chatgpt_reachable": True,
            "api_reachable": None,
            "error": None,
            "success_rate": 1.0,
            "failure_reasons": [],
            "latency_histogram": [],
            "tls_connect_success": True,
            "latency_ms": None,
        },
        {
            "name": "HK-Dedicated-HongKong",
            "categories": ["dedicated", "hong_kong"],
            "openai": False,
            "mode": "mock",
            "reason": "mock: not a direct JP/SG/US candidate",
            "checked_at": "2026-07-01T00:00:00+00:00",
            "chatgpt_reachable": False,
            "api_reachable": None,
            "error": "mock: not a direct JP/SG/US candidate",
            "success_rate": 0.0,
            "failure_reasons": ["mock: not a direct JP/SG/US candidate"],
            "latency_histogram": [],
            "tls_connect_success": False,
            "latency_ms": None,
        },
    ]


def test_real_mode_uses_monkeypatched_network_requests(monkeypatch) -> None:
    calls = []

    def fake_request(url: str, timeout: float, headers=None):
        calls.append((url, timeout, headers))
        return True, 200, None

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(check_openai, "request_url", fake_request)
    monkeypatch.setattr(check_openai, "now_iso", lambda: "2026-07-01T00:00:00+00:00")

    results = check_nodes(["JP-Direct-Tokyo"], mode="real")

    assert results[0]["openai"] is True
    assert results[0]["chatgpt_reachable"] is True
    assert results[0]["api_reachable"] is True
    assert results[0]["error"] is None
    assert results[0]["success_rate"] == 1.0
    assert results[0]["failure_reasons"] == []
    assert len(results[0]["latency_histogram"]) == 2
    assert results[0]["tls_connect_success"] is True
    assert results[0]["latency_ms"] >= 0
    assert [call[0] for call in calls] == [
        check_openai.CHATGPT_TRACE_URL,
        check_openai.OPENAI_MODELS_URL,
    ]
    assert calls[1][2]["Authorization"] == "Bearer test-key"


def test_real_mode_without_openai_api_key_skips_api_request(monkeypatch) -> None:
    calls = []

    def fake_request(url: str, timeout: float, headers=None):
        calls.append(url)
        return True, 200, None

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(check_openai, "request_url", fake_request)

    results = check_nodes(["JP-Direct-Tokyo"], mode="real")

    assert results[0]["openai"] is True
    assert results[0]["chatgpt_reachable"] is True
    assert results[0]["api_reachable"] is None
    assert results[0]["success_rate"] == 1.0
    assert len(results[0]["latency_histogram"]) == 1
    assert calls == [check_openai.CHATGPT_TRACE_URL]
