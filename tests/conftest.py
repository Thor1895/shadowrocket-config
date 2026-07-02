from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def default_mock_subscribe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUBSCRIBE_URL", str(ROOT / "tests" / "fixtures" / "mock_subscribe.txt"))
