from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.openai_health import (
    CHATGPT_TRACE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    OPENAI_MODELS_URL,
    check_nodes,
    load_candidate_names,
    main,
    mock_check_node,
    mock_result_for_node,
    now_iso,
    real_check_node,
    render_json,
    render_markdown,
    request_url,
    write_health_files,
)


if __name__ == "__main__":
    raise SystemExit(main())
