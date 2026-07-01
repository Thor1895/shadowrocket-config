from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def ensure_git_repo() -> bool:
    result = git("rev-parse", "--is-inside-work-tree", check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def remote_ref_exists() -> bool:
    result = git("rev-parse", "--verify", "origin/main", check=False)
    return result.returncode == 0


def fetch_remote_main() -> None:
    result = git("fetch", "--quiet", "origin", "main", check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "failed to fetch origin/main")


def remote_is_in_local_history() -> bool:
    result = git("merge-base", "--is-ancestor", "origin/main", "HEAD", check=False)
    return result.returncode == 0


def main() -> int:
    if os.environ.get("SKIP_SYNC_GUARD") == "1":
        return 0

    if not ensure_git_repo():
        print("sync_guard: not inside a git repository; skipping remote freshness check")
        return 0

    try:
        fetch_remote_main()
    except RuntimeError as exc:
        print(f"sync_guard: warning: {exc}", file=sys.stderr)
        print("sync_guard: unable to verify origin/main freshness; build blocked", file=sys.stderr)
        return 1

    if not remote_ref_exists():
        print("sync_guard: warning: origin/main does not exist; build blocked", file=sys.stderr)
        return 1

    if remote_is_in_local_history():
        return 0

    print("sync_guard: remote main has commits that are not in local HEAD.", file=sys.stderr)
    print("sync_guard: run `git pull --rebase` before building or pushing.", file=sys.stderr)
    print("sync_guard: this prevents future push conflicts in generated output.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
