from __future__ import annotations

import base64

from services.subscription_loader import parse_subscription


def test_parse_plaintext_subscription() -> None:
    nodes = parse_subscription("""
# comment
ss://abc#日本
trojan://pass@example.test:443#US
""")

    assert nodes == ["ss://abc#日本", "trojan://pass@example.test:443#US"]


def test_parse_base64_subscription() -> None:
    payload = "ss://abc#日本\nvmess://def#新加坡\n"
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")

    assert parse_subscription(encoded) == ["ss://abc#日本", "vmess://def#新加坡"]
