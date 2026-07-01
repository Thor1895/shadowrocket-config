from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.classify_nodes import load_nodes, openai_default_nodes, streaming_nodes

OUTPUT = ROOT / "output" / "shadowrocket.conf"

AI_GROUPS = {"OpenAI", "Gemini", "Claude"}
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


def validate() -> None:
    lines = read_lines()
    for header in ("[General]", "[Proxy]", "[Proxy Group]", "[Rule]"):
        if header not in lines:
            raise AssertionError(f"missing {header} section")

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
    openai_nodes = openai_default_nodes(nodes)
    if set(groups["OpenAI"]) - set(openai_nodes):
        raise AssertionError("OpenAI group may only contain direct Japan, Singapore, and United States nodes")

    if groups["OpenAI"] != openai_nodes:
        raise AssertionError("OpenAI group must default to direct Japan, Singapore, and United States nodes")

    streaming = groups.get("Streaming")
    if not streaming:
        raise AssertionError("missing or empty Streaming group")
    expected_streaming_nodes = streaming_nodes(nodes)
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
