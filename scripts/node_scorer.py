from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.scorer import (
    default_success_rate,
    health_success_rate,
    latency_from_health,
    load_health,
    load_top_nodes,
    main,
    mock_latency_ms,
    mock_packet_loss,
    now_iso,
    region_penalty,
    score_node,
    score_nodes,
    tls_success,
    top_nodes,
    write_scores,
)


if __name__ == "__main__":
    raise SystemExit(main())
