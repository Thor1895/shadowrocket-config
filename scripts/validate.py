from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.constants import AI_SERVICES, NODE_SCORE_FILE, SHADOWROCKET_FILE
from core.router import route
from services.rule_loader import load_nodes

OUTPUT = SHADOWROCKET_FILE

AI_GROUPS = AI_SERVICES
SAMPLE_NODE_NAMES = {
    "MO-Relay-Macau",
    "HK-Dedicated-HongKong",
    "US-Direct-LosAngeles",
    "SG-Direct-Singapore",
    "JP-Direct-Tokyo",
}
NODE_PROTOCOL_PREFIXES = ("ss,", "vmess,", "vless,", "trojan,")
BANNED_EXAMPLE_TOKENS = {"jp.example.com", "sg.example.com", "change-me"}

DIRECT_DOMAINS = {
    "alipay.com",
    "alipayobjects.com",
    "antfin.com",
    "wechat.com",
    "weixin.qq.com",
    "qq.com",
    "amap.com",
    "autonavi.com",
    "meituan.com",
    "dianping.com",
    "ele.me",
    "elemecdn.com",
    "icbc.com.cn",
    "ccb.com",
    "abchina.com",
    "boc.cn",
    "bankcomm.com",
    "cmbchina.com",
    "psbc.com",
    "spdb.com.cn",
    "cib.com.cn",
}


def read_lines() -> list[str]:
    if not OUTPUT.exists():
        raise AssertionError("output/shadowrocket.conf does not exist; run python build.py first")
    return [line.strip() for line in OUTPUT.read_text(encoding="utf-8").splitlines()]


def section(lines: list[str], header: str) -> list[str]:
    start = lines.index(header) + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("[") and lines[index].endswith("]"):
            end = index
            break
    return [line for line in lines[start:end] if line and not line.startswith("#")]


def parse_groups(lines: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for line in section(lines, "[Proxy Group]"):
        name, raw_members = line.split("=", 1)
        parts = [part.strip() for part in raw_members.split(",")]
        groups[name.strip()] = parts[1:]
    return groups


def parse_rules(lines: list[str]) -> list[tuple[str, ...]]:
    return [tuple(part.strip() for part in line.split(",")) for line in section(lines, "[Rule]")]


def validate_proxy_section(lines: list[str]) -> None:
    proxy_lines = section(lines, "[Proxy]")
    for line in proxy_lines:
        if " = " in line and any(prefix in line for prefix in NODE_PROTOCOL_PREFIXES):
            raise AssertionError("[Proxy] section must not contain built-in node definitions")


def validate_no_sample_nodes(text: str) -> None:
    for name in SAMPLE_NODE_NAMES:
        if name in text:
            raise AssertionError(f"generated config must not contain sample node {name}")
    for token in BANNED_EXAMPLE_TOKENS:
        if token in text:
            raise AssertionError(f"generated config must not contain example token {token}")


def validate_regex_groups(lines: list[str]) -> None:
    for line in section(lines, "[Proxy Group]"):
        if "policy-regex-filter=" in line and "use=true" not in line:
            raise AssertionError(f"regex policy group must include use=true: {line}")


def validate() -> None:
    text = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    lines = read_lines()
    for header in ("[General]", "[Proxy]", "[Proxy Group]", "[Rule]"):
        if header not in lines:
            raise AssertionError(f"missing {header} section")

    validate_proxy_section(lines)
    validate_no_sample_nodes(text)
    validate_regex_groups(lines)

    groups = parse_groups(lines)
    rules = parse_rules(lines)

    if "PROXY" not in groups:
        raise AssertionError("missing PROXY group")

    for name in AI_GROUPS:
        members = groups.get(name)
        if not members:
            raise AssertionError(f"missing or empty {name} group")
        if "PROXY" in members:
            raise AssertionError(f"{name} must not include PROXY")

    nodes = load_nodes()
    selected_ai_nodes = route("OpenAI", nodes, score_path=NODE_SCORE_FILE)
    for name in AI_GROUPS:
        if groups[name] != selected_ai_nodes:
            raise AssertionError(f"{name} group must match scored top AI nodes")

    streaming = groups.get("Streaming")
    if not streaming:
        raise AssertionError("missing or empty Streaming group")
    expected_streaming_nodes = route("Streaming", nodes, score_path=NODE_SCORE_FILE)
    if streaming != expected_streaming_nodes:
        raise AssertionError("Streaming group must prefer dedicated nodes")

    for domain in ("xiaohongshu.com", "xhscdn.com"):
        if ("DOMAIN-SUFFIX", domain, "PROXY") not in rules:
            raise AssertionError(f"{domain} must route to PROXY")

    for domain in DIRECT_DOMAINS:
        if ("DOMAIN-SUFFIX", domain, "DIRECT") not in rules:
            raise AssertionError(f"{domain} must route to DIRECT")

    for domain, target in (
        ("openai.com", "OpenAI"),
        ("chatgpt.com", "OpenAI"),
        ("gemini.google.com", "Gemini"),
        ("anthropic.com", "Claude"),
        ("claude.ai", "Claude"),
        ("netflix.com", "Streaming"),
        ("youtube.com", "Streaming"),
    ):
        if ("DOMAIN-SUFFIX", domain, target) not in rules:
            raise AssertionError(f"{domain} must route to {target}")


def main() -> int:
    try:
        validate()
    except AssertionError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Validation passed: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
