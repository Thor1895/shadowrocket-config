from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import release_meta


def test_release_download_url_uses_latest_release_asset() -> None:
    assert (
        release_meta.release_download_url("Thor1895/shadowrocket-config")
        == "https://github.com/Thor1895/shadowrocket-config/releases/latest/download/shadowrocket.conf"
    )


def test_write_metadata_outputs_version_url_and_sha256(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "shadowrocket.conf"
    config.write_text("[General]\n", encoding="utf-8")
    output = tmp_path / "latest.json"
    monkeypatch.setenv("GITHUB_SHA", "1234567890abcdef")

    release_meta.write_metadata(
        config_path=config,
        output_path=output,
        repo="Thor1895/shadowrocket-config",
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    expected_sha = hashlib.sha256(config.read_bytes()).hexdigest()
    assert payload["version"] == "1234567890ab"
    assert payload["raw_url"] == "https://github.com/Thor1895/shadowrocket-config/releases/latest/download/shadowrocket.conf"
    assert payload["download_url"] == payload["raw_url"]
    assert payload["sha256"] == expected_sha
    assert payload["timestamp"]
