# shadowrocket-config

[![Build Shadowrocket Config](https://github.com/Thor1895/shadowrocket-config/actions/workflows/build.yml/badge.svg)](https://github.com/Thor1895/shadowrocket-config/actions/workflows/build.yml)

Python + YAML + Jinja2 based Shadowrocket configuration generator.

## Status

GitHub Actions runs on every push to `main`:

```text
python3 scripts/check_openai.py --mode mock
python3 build.py
python3 scripts/validate.py
python3 -m pytest -q
```

The workflow also uploads `output/shadowrocket.conf` as a build artifact.

## Layout

```text
.
├── build.py
├── config/
│   ├── nodes.yaml
│   ├── rules.yaml
│   └── settings.yaml
├── templates/
│   └── shadowrocket.conf.j2
├── scripts/
│   └── validate.py
├── tests/
│   └── test_build.py
└── output/
    └── shadowrocket.conf
```

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate the Shadowrocket config:

```bash
python build.py
```

Validate the generated config:

```bash
python scripts/validate.py
pytest
```

## Shadowrocket Import

Use this GitHub raw URL in Shadowrocket as a remote configuration subscription:

```text
https://raw.githubusercontent.com/Thor1895/shadowrocket-config/main/output/shadowrocket.conf
```

See [docs/import-shadowrocket.md](docs/import-shadowrocket.md) for import steps.

## Routing Policy

- OpenAI, Gemini, and Claude each have an independent policy group and do not use `PROXY`.
- OpenAI candidates are limited to direct Japan, Singapore, and United States nodes.
- Streaming routes use the `Streaming` group, which prefers dedicated line nodes before falling back to all nodes.
- Xiaohongshu routes through `PROXY`.
- Alipay, WeChat, Amap, Meituan, Ele.me, and bank domains route through `DIRECT`.

## Node Naming Rules

Node classification is inferred from each node's `name` in `config/nodes.yaml`.

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
python3 scripts/check_openai.py --input config/nodes.yaml
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

## Daily Maintenance

1. Update nodes in `config/nodes.yaml`.
2. Update routing rules in `config/rules.yaml`.
3. Regenerate the outputs:

   ```bash
   python3 scripts/classify_nodes.py
   python3 scripts/check_openai.py --mode mock
   python3 build.py
   ```

4. Validate locally:

   ```bash
   python3 scripts/validate.py
   python3 -m pytest -q
   ```

5. Commit `config/`, templates or scripts, tests, and the regenerated `output/shadowrocket.conf`.
6. Push to `main` and confirm the GitHub Actions run passes.
