from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.classify_nodes import (
    classify_node_name,
    load_nodes,
    openai_default_nodes,
    streaming_nodes,
    write_report,
)


def test_classify_node_name_recognizes_type_and_region() -> None:
    assert {"direct", "japan"}.issubset(classify_node_name("JP-Direct-Tokyo"))
    assert {"direct", "singapore"}.issubset(classify_node_name("SG-直连-新加坡"))
    assert {"relay", "macau"}.issubset(classify_node_name("MO-Relay-Macau"))
    assert {"dedicated", "hong_kong"}.issubset(classify_node_name("HK-专线-HongKong"))
    assert {"direct", "united_states"}.issubset(classify_node_name("US-Direct-LosAngeles"))


def test_openai_defaults_to_direct_jp_sg_us_nodes() -> None:
    nodes = load_nodes()

    assert openai_default_nodes(nodes) == [
        "JP-Direct-Tokyo",
        "SG-Direct-Singapore",
        "US-Direct-LosAngeles",
    ]


def test_streaming_prefers_dedicated_nodes() -> None:
    nodes = load_nodes()
    members = streaming_nodes(nodes)

    assert members[0] == "HK-Dedicated-HongKong"
    assert set(members) == {node["name"] for node in nodes}


def test_node_groups_report_can_be_written(tmp_path: Path) -> None:
    report_path = tmp_path / "node_groups_report.md"

    write_report(report_path)

    report = report_path.read_text(encoding="utf-8")
    assert "Direct / 直连" in report
    assert "Dedicated / 专线" in report
    assert "- JP-Direct-Tokyo" in report
    assert "- HK-Dedicated-HongKong" in report
