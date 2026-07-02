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
    assert groups["OpenAI"] == ["日本节点", "新加坡节点", "美国节点"]


def test_proxy_uses_all_nodes_and_streaming_prefers_dedicated_nodes() -> None:
    output = build.build()
    lines = [line.strip() for line in output.read_text(encoding="utf-8").splitlines()]
    groups = parse_groups(lines)

    assert groups["PROXY"] == ["use=true", "policy-regex-filter=.*", "url=http://cp.cloudflare.com/generate_204", "interval=300", "timeout=3", "tolerance=20"]
    assert groups["Streaming"][0] == "专线节点"
    assert "香港节点" in groups["Streaming"]


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
    assert ("DOMAIN-SUFFIX", "netflix.com", "Streaming") in rules
    assert ("DOMAIN-SUFFIX", "youtube.com", "Streaming") in rules


def test_validate_script_rules_pass() -> None:
    build.build()
    validate()


def test_proxy_section_does_not_contain_sample_nodes() -> None:
    output = build.build()
    text = output.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    proxy_lines = [line for line in lines[lines.index("[Proxy]") + 1:lines.index("[Proxy Group]")] if line]

    assert proxy_lines == ["# 节点由 Shadowrocket 中单独添加的机场订阅提供，本配置不内置任何节点。"]
    for sample in ["MO-Relay-Macau", "HK-Dedicated-HongKong", "US-Direct-LosAngeles", "SG-Direct-Singapore", "JP-Direct-Tokyo"]:
        assert sample not in text


def test_regex_policy_groups_include_use_true() -> None:
    output = build.build()
    lines = [line.strip() for line in output.read_text(encoding="utf-8").splitlines()]
    group_lines = [line for line in lines[lines.index("[Proxy Group]") + 1:lines.index("[Rule]")] if line]

    regex_groups = [line for line in group_lines if "policy-regex-filter=" in line]
    assert regex_groups
    assert all("use=true" in line for line in regex_groups)


def test_proxy_group_is_subscription_regex_filter() -> None:
    output = build.build()
    lines = [line.strip() for line in output.read_text(encoding="utf-8").splitlines()]
    proxy_group_line = next(line for line in lines if line.startswith("PROXY = "))

    assert proxy_group_line == "PROXY = url-test,use=true,policy-regex-filter=.*,url=http://cp.cloudflare.com/generate_204,interval=300,timeout=3,tolerance=20"
