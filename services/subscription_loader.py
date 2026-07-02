from __future__ import annotations

import base64
import os
from pathlib import Path
from urllib.request import Request, urlopen


SUBSCRIBE_ENV = "SUBSCRIBE_URL"
USER_AGENT = "shadowrocket-config-private-builder/1.0"


def _read_subscription_source(source: str) -> str:
    if source.startswith(("http://", "https://")):
        request = Request(source, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")

    path = Path(source).expanduser()
    if path.exists():
        return path.read_text(encoding="utf-8")

    raise ValueError("SUBSCRIBE_URL must be an http(s) URL or an existing local fixture path")


def _decode_base64_if_needed(content: str) -> str:
    compact = "".join(content.strip().split())
    if not compact:
        return content

    padding = "=" * (-len(compact) % 4)
    try:
        decoded = base64.b64decode(compact + padding, validate=False).decode("utf-8")
    except Exception:
        return content

    markers = ("ss://", "vmess://", "vless://", "trojan://", "hysteria://", "tuic://", " = ")
    if any(marker in decoded for marker in markers):
        return decoded
    return content


def parse_subscription(content: str) -> list[str]:
    decoded = _decode_base64_if_needed(content)
    nodes: list[str] = []
    for raw_line in decoded.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        nodes.append(line)
    return nodes


def load_subscription_nodes(source: str | None = None) -> list[str]:
    source = source or os.environ.get(SUBSCRIBE_ENV)
    if not source:
        return []
    return parse_subscription(_read_subscription_source(source))
