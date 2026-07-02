# shadowrocket-config

[![Build Shadowrocket Config](https://github.com/Thor1895/shadowrocket-config/actions/workflows/build.yml/badge.svg)](https://github.com/Thor1895/shadowrocket-config/actions/workflows/build.yml)

Python + YAML + Jinja2 based Shadowrocket configuration generator.

## Private Build Mode

This repository is now designed for private local builds. `build.py` reads your airport subscription from `SUBSCRIBE_URL`, embeds those nodes into `[Proxy]`, and generates a complete Shadowrocket config for your own device.

`output/shadowrocket.conf` contains subscription nodes, passwords, and tokens. Do not commit it to a public GitHub repository, upload it as a public artifact, or publish it as a Release asset. The file is ignored by Git.

Local build:

```bash
export SUBSCRIBE_URL='你的订阅链接'
SKIP_SYNC_GUARD=1 python3 build.py
python3 scripts/validate.py
```

`SUBSCRIBE_URL` may point to an `https://` subscription or a local fixture file. The value is never written to the generated config, `output/latest.json`, logs, or README examples.

## Status

GitHub Actions runs on every push to `main`:

```text
python3 scripts/check_openai.py --mode mock
python3 scripts/node_scorer.py
python3 build.py
python3 scripts/validate.py
python3 scripts/complexity_check.py
python3 -m pytest -q
```

CI uses `tests/fixtures/mock_subscribe.txt` as `SUBSCRIBE_URL`. It does not use a real subscription URL. Auto-publishing is disabled because private builds embed subscription nodes and credentials.

## Layout

```text
.
├── build.py
├── core/
│   ├── classifier.py
│   ├── constants.py
│   ├── router.py
│   └── scorer.py
├── data/
│   ├── nodes.yaml
│   ├── rules.yaml
│   └── settings.yaml
├── jobs/
│   ├── build.py
│   └── release.py
├── services/
│   ├── node_health.py
│   ├── openai_health.py
│   └── rule_loader.py
├── templates/
│   └── shadowrocket.conf.j2
├── scripts/
│   ├── complexity_check.py
│   └── validate.py
├── tests/
│   └── test_build.py
└── output/
    └── shadowrocket.conf  # local only, ignored by Git
```

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the Shadowrocket config:

```bash
export SUBSCRIBE_URL='你的订阅链接'
SKIP_SYNC_GUARD=1 python3 build.py
```

Validate the generated config:

```bash
python scripts/validate.py
pytest
```

## Shadowrocket Import

Import the locally generated `output/shadowrocket.conf` into Shadowrocket manually. Do not use a public raw URL or public Release URL for private builds.

## Routing Policy

- OpenAI, Gemini, and Claude each have an independent policy group and do not use `PROXY`.
- OpenAI candidates are limited to direct Japan, Singapore, and United States nodes.
- Streaming routes use the `Streaming` group, which prefers dedicated line nodes before falling back to all nodes.
- Xiaohongshu routes through `PROXY`.
- Alipay, WeChat, Amap, Meituan, Ele.me, and bank domains route through `DIRECT`.

## Node Naming Rules

Node classification is inferred from each node's `name` in `data/nodes.yaml`.

Recommended format:

```text
<Region>-<LineType>-<CityOrLabel>
```

Examples:

```text
JP-Direct-Tokyo
SG-Direct-Singapore
US-Direct-LosAngeles
HK-Dedicated-HongKong
MO-Relay-Macau
```

Recognized line type keywords:

- Direct / `直连`: `Direct`, `直连`
- Relay / `中转`: `Relay`, `Transit`, `中转`
- Dedicated / `专线`: `Dedicated`, `IPLC`, `IEPL`, `Premium`, `专线`

Recognized region keywords:

- Hong Kong / `香港`: `HK`, `HongKong`, `Hong Kong`, `香港`
- Macau / `澳门`: `MO`, `Macau`, `Macao`, `澳门`
- Japan / `日本`: `JP`, `Japan`, `Tokyo`, `Osaka`, `日本`, `东京`, `大阪`
- Singapore / `新加坡`: `SG`, `Singapore`, `新加坡`
- United States / `美国`: `US`, `USA`, `United States`, `America`, `LosAngeles`, `Los Angeles`, `美国`, `洛杉矶`

Generate the node classification report:

```bash
python3 scripts/classify_nodes.py
```

The report is written to `output/node_groups_report.md`.

## OpenAI Health Check

OpenAI routing can use a generated health file:

```bash
python3 scripts/check_openai.py --mode mock
python3 build.py
```

The first command writes:

- `output/openai_health.json`
- `output/openai_health.md`

When `output/openai_health.json` exists, `build.py` puts nodes with `openai=true` into the `OpenAI` group first. If the health file is missing or has no usable `openai=true` nodes, the build falls back to direct Japan, Singapore, and United States candidates.

The checker also accepts a node sample list or the classification report:

```bash
python3 scripts/check_openai.py --input output/node_groups_report.md
python3 scripts/check_openai.py --input data/nodes.yaml
```

Mock mode is the default:

```bash
python3 scripts/check_openai.py
python3 scripts/check_openai.py --mode mock
```

Mock mode does not open real network connections. It marks direct Japan, Singapore, and United States nodes as `openai=true`, which gives the generator a deterministic baseline for local development and CI.

Real mode performs direct access checks from the machine running the script:

```bash
python3 scripts/check_openai.py --mode real
```

Real mode requests:

- `https://chatgpt.com/cdn-cgi/trace`
- `https://api.openai.com/v1/models`, only when `OPENAI_API_KEY` is set

`OPENAI_API_KEY` is optional. Without it, real mode only checks `chatgpt.com`; with it, the checker also verifies the OpenAI API endpoint.

GitHub Actions intentionally uses mock mode. Real OpenAI checks depend on the runner's network, region, rate limits, API key availability, and transient service conditions, so CI should verify generator behavior without making release status depend on external connectivity.

OpenAI does not use `url-test` automatic latency selection because latency is not the same as OpenAI availability. A low-latency node may still be blocked, challenged, region-mismatched, or unable to reach OpenAI services reliably. The explicit health file keeps OpenAI routing based on service availability rather than generic speed.

## Node Scoring

AI routing is score driven. Generate scores with:

```bash
python3 scripts/node_scorer.py
```

The scorer writes `output/node_score.json` and ranks nodes with these dimensions:

- `latency_ms`
- `openai_success_rate`
- `tls_connect_success`
- `packet_loss`
- `region_penalty`, which lowers Hong Kong and Macau nodes for AI routing

`build.py` reads `output/node_score.json` and assigns the top 3 nodes to `OpenAI`, `Gemini`, and `Claude`. If the score file is missing, the generator falls back to direct Japan, Singapore, and United States candidates so a clean checkout can still build.

Scoring is more reliable than Shadowrocket `url-test` for AI routes because `url-test` only measures generic endpoint latency. AI services need more context: service reachability, TLS success, recent OpenAI health, packet loss, and region risk. A fast node can still be a bad AI node if it is blocked, challenged, or unstable for the target service.

AI routing must be dynamic because provider access changes by region, ASN, IP reputation, and time. The score file lets the repository update routing decisions from measured health data while keeping the subscription URL stable.

## Architecture Boundaries

The production code is split by responsibility:

- `core/router.py`: final route decision engine for `OpenAI`, `Gemini`, `Claude`, `PROXY`, `Streaming`, bank, and China app routing.
- `core/scorer.py`: the only scoring engine.
- `core/classifier.py`: node name classification.
- `services/openai_health.py` and `services/node_health.py`: health data providers.
- `services/rule_loader.py`: YAML loading.
- `jobs/build.py`: orchestration layer that loads inputs, calls router/scorer/classifier through their public APIs, and renders the template.

`scripts/complexity_check.py` enforces those boundaries in CI. It fails when routing leaks into build entrypoints, scoring leaks into router, duplicate rule-sets appear, or another scoring system is introduced.

## Daily Maintenance

1. Update nodes in `data/nodes.yaml`.
2. Update routing rules in `data/rules.yaml`.
3. Regenerate the outputs:

   ```bash
   python3 scripts/classify_nodes.py
   python3 scripts/check_openai.py --mode mock
   python3 scripts/node_scorer.py
   export SUBSCRIBE_URL='你的订阅链接'
   SKIP_SYNC_GUARD=1 python3 build.py
   ```

4. Validate locally:

   ```bash
   python3 scripts/validate.py
   python3 -m pytest -q
   ```

5. Commit source changes under `data/`, `core/`, `services/`, `jobs/`, `templates/`, `scripts/`, `tests/`, and docs. Do not commit `output/shadowrocket.conf`.
6. Push to `main` and confirm the GitHub Actions run passes.

## Generated Output Policy

Do not manually edit files in `output/`. They are generated artifacts, not the source of truth. `output/shadowrocket.conf` is private and ignored by Git because it contains subscription nodes and credentials.

Always generate Shadowrocket config through:

```bash
python3 build.py
```

`build.py` is the single generation entry point. It applies the YAML config, Jinja2 template, OpenAI health data, node classification rules, and validation assumptions consistently.

The intended ownership model is:

- GitHub is the configuration source.
- Codex is the generation engine.
- `output/shadowrocket.conf` is generated locally and kept private.

## Git Conflict Strategy

Before local maintenance, update from GitHub with rebase:

```bash
git pull --rebase
```

Then make source changes, build or validate locally, commit, and push:

```bash
git push
```

Prefer rebase over merge commits for this repository. Merge commits make generated-output history harder to reason about and can reintroduce old generated files during conflict resolution.

Do not force push unless the repository is being intentionally rebuilt from scratch. Force pushes can discard generated config commits produced by GitHub Actions and make other local clones stale.

`scripts/sync_guard.py` checks whether `origin/main` has commits missing from local `HEAD`. `python3 build.py` runs this guard before generating locally, so a stale checkout is blocked before it creates output that would later conflict on push.
