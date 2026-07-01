from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build
from scripts.validate import parse_groups, parse_rules, validate


def test_build_generates_shadowrocket_config() -> None:
    output = build.build()

    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "[General]" in text
    assert "[Proxy]" in text
    assert "[Proxy Group]" in text
    assert "[Rule]" in text


def test_ai_groups_are_independent_from_proxy() -> None:
    output = build.build()
    lines = [line.strip() for line in output.read_text(encoding="utf-8").splitlines()]
    groups = parse_groups(lines)

    assert "PROXY" not in groups["OpenAI"]
    assert "PROXY" not in groups["Gemini"]
    assert "PROXY" not in groups["Claude"]
    assert set(groups["OpenAI"]) == {"JP-Tokyo", "SG-Singapore", "US-LosAngeles"}


def test_required_routes() -> None:
    output = build.build()
    lines = [line.strip() for line in output.read_text(encoding="utf-8").splitlines()]
    rules = parse_rules(lines)

    assert ("DOMAIN-SUFFIX", "xiaohongshu.com", "PROXY") in rules
    assert ("DOMAIN-SUFFIX", "alipay.com", "DIRECT") in rules
    assert ("DOMAIN-SUFFIX", "wechat.com", "DIRECT") in rules
    assert ("DOMAIN-SUFFIX", "amap.com", "DIRECT") in rules
    assert ("DOMAIN-SUFFIX", "meituan.com", "DIRECT") in rules
    assert ("DOMAIN-SUFFIX", "ele.me", "DIRECT") in rules
    assert ("DOMAIN-SUFFIX", "icbc.com.cn", "DIRECT") in rules


def test_validate_script_rules_pass() -> None:
    build.build()
    validate()
