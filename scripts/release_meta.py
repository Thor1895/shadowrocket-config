from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jobs.release import (
    build_metadata,
    current_version,
    git,
    main,
    release_download_url,
    repository_slug,
    sha256_file,
    write_metadata,
)


if __name__ == "__main__":
    raise SystemExit(main())
