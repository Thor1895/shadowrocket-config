from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build
from scripts.check_openai import check_nodes, load_candidate_names, write_health_files
from scripts.validate import parse_groups


def _groups_from_output(path: Path) -> dict[str, list[str]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return parse_groups(lines)


def test_build_prefers_openai_true_nodes_from_health_file(tmp_path: Path, monkeypatch) -> None:
    health_path = tmp_path / "openai_health.json"
    health_path.write_text(
        json.dumps(
            {
                "results": [
                    {"name": "JP-Direct-Tokyo", "openai": False},
                    {"name": "HK-Dedicated-HongKong", "openai": True},
                    {"name": "Unknown-Node", "openai": True},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(build, "OPENAI_HEALTH_FILE", health_path)

    output = build.build()
    groups = _groups_from_output(output)

    assert groups["OpenAI"] == ["HK-Dedicated-HongKong"]


def test_build_falls_back_to_default_openai_candidates_without_health_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(build, "OPENAI_HEALTH_FILE", tmp_path / "missing_openai_health.json")

    output = build.build()
    groups = _groups_from_output(output)

    assert groups["OpenAI"] == ["JP-Direct-Tokyo", "SG-Direct-Singapore", "US-Direct-LosAngeles"]


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
