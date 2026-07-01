from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.constants import DEFAULT_REPO, LATEST_JSON, ROOT, SHADOWROCKET_FILE


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def current_version() -> str:
    env_sha = os.environ.get("GITHUB_SHA")
    if env_sha:
        return env_sha[:12]
    return git("rev-parse", "--short=12", "HEAD")


def repository_slug() -> str:
    env_repo = os.environ.get("GITHUB_REPOSITORY")
    if env_repo:
        return env_repo

    try:
        remote = git("remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        return DEFAULT_REPO

    match = re.search(r"github\.com[:/](?P<repo>[^/]+/[^/.]+)(?:\.git)?$", remote)
    if match:
        return match.group("repo")
    return DEFAULT_REPO


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_download_url(repo: str) -> str:
    return f"https://github.com/{repo}/releases/latest/download/shadowrocket.conf"


def build_metadata(config_path: Path = SHADOWROCKET_FILE, repo: str | None = None) -> dict[str, Any]:
    repo = repo or repository_slug()
    download_url = release_download_url(repo)
    return {
        "version": current_version(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_url": download_url,
        "download_url": download_url,
        "sha256": sha256_file(config_path),
    }


def write_metadata(
    config_path: Path = SHADOWROCKET_FILE,
    output_path: Path = LATEST_JSON,
    repo: str | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = build_metadata(config_path=config_path, repo=repo)
    output_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate release metadata for the Shadowrocket subscription.")
    parser.add_argument("--config", type=Path, default=SHADOWROCKET_FILE, help="Generated Shadowrocket config path.")
    parser.add_argument("--output", type=Path, default=LATEST_JSON, help="Metadata JSON output path.")
    parser.add_argument("--repo", help="GitHub repository slug, for example Thor1895/shadowrocket-config.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = write_metadata(config_path=args.config, output_path=args.output, repo=args.repo)
    print(f"Generated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
