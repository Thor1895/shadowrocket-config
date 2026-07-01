from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import sync_guard


def test_sync_guard_allows_skip_env(monkeypatch) -> None:
    monkeypatch.setenv("SKIP_SYNC_GUARD", "1")
    monkeypatch.setattr(sync_guard, "ensure_git_repo", lambda: (_ for _ in ()).throw(AssertionError("should skip")))

    assert sync_guard.main() == 0


def test_sync_guard_blocks_when_remote_is_newer(monkeypatch) -> None:
    monkeypatch.delenv("SKIP_SYNC_GUARD", raising=False)
    monkeypatch.setattr(sync_guard, "ensure_git_repo", lambda: True)
    monkeypatch.setattr(sync_guard, "fetch_remote_main", lambda: None)
    monkeypatch.setattr(sync_guard, "remote_ref_exists", lambda: True)
    monkeypatch.setattr(sync_guard, "remote_is_in_local_history", lambda: False)

    assert sync_guard.main() == 1


def test_sync_guard_allows_current_checkout(monkeypatch) -> None:
    monkeypatch.delenv("SKIP_SYNC_GUARD", raising=False)
    monkeypatch.setattr(sync_guard, "ensure_git_repo", lambda: True)
    monkeypatch.setattr(sync_guard, "fetch_remote_main", lambda: None)
    monkeypatch.setattr(sync_guard, "remote_ref_exists", lambda: True)
    monkeypatch.setattr(sync_guard, "remote_is_in_local_history", lambda: True)

    assert sync_guard.main() == 0
