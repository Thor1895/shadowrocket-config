from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"

NODES_FILE = DATA_DIR / "nodes.yaml"
RULES_FILE = DATA_DIR / "rules.yaml"
SETTINGS_FILE = DATA_DIR / "settings.yaml"

SHADOWROCKET_FILE = OUTPUT_DIR / "shadowrocket.conf"
NODE_GROUPS_REPORT_FILE = OUTPUT_DIR / "node_groups_report.md"
OPENAI_HEALTH_JSON = OUTPUT_DIR / "openai_health.json"
OPENAI_HEALTH_MD = OUTPUT_DIR / "openai_health.md"
NODE_SCORE_FILE = OUTPUT_DIR / "node_score.json"
LATEST_JSON = OUTPUT_DIR / "latest.json"

AI_SERVICES = {"OpenAI", "Gemini", "Claude"}
BANK_AND_CHINA_APP_TARGET = "DIRECT"
DEFAULT_REPO = "Thor1895/shadowrocket-config"

TYPE_ALIASES = {
    "direct": ("direct", "直连"),
    "relay": ("relay", "中转", "transit"),
    "dedicated": ("dedicated", "iplc", "iepl", "premium", "专线"),
}

REGION_ALIASES = {
    "hong_kong": ("hk", "hongkong", "hong kong", "香港"),
    "macau": ("mo", "macau", "macao", "澳门"),
    "japan": ("jp", "japan", "tokyo", "osaka", "日本", "东京", "大阪"),
    "singapore": ("sg", "singapore", "新加坡"),
    "united_states": ("us", "usa", "united states", "america", "losangeles", "los angeles", "美国", "洛杉矶"),
}

AI_FALLBACK_REGIONS = {"japan", "singapore", "united_states"}
REGION_PENALTIES = {
    "hong_kong": 20,
    "macau": 25,
}

REGION_POLICY_GROUPS = {
    "japan": "日本节点",
    "singapore": "新加坡节点",
    "united_states": "美国节点",
    "hong_kong": "香港节点",
    "macau": "澳门节点",
}

REGION_POLICY_REGEX = {
    "日本节点": "日本|JP|Japan|Tokyo|东京",
    "新加坡节点": "新加坡|SG|Singapore",
    "美国节点": "美国|US|USA|United States|America",
    "香港节点": "香港|HK|Hong Kong|HongKong",
    "澳门节点": "澳门|MO|Macau|Macao",
    "专线节点": "专线|IPLC|IEPL|Dedicated|Premium",
}

URL_TEST_OPTIONS = [
    "use=true",
    "url=http://cp.cloudflare.com/generate_204",
    "interval=300",
    "timeout=3",
    "tolerance=20",
]
