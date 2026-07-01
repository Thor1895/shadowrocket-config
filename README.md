# shadowrocket-config

[![Build Shadowrocket Config](https://github.com/Thor1895/shadowrocket-config/actions/workflows/build.yml/badge.svg)](https://github.com/Thor1895/shadowrocket-config/actions/workflows/build.yml)

Python + YAML + Jinja2 based Shadowrocket configuration generator.

## Status

GitHub Actions runs on every push to `main`:

```text
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

## Daily Maintenance

1. Update nodes in `config/nodes.yaml`.
2. Update routing rules in `config/rules.yaml`.
3. Regenerate the outputs:

   ```bash
   python3 build.py
   python3 scripts/classify_nodes.py
   ```

4. Validate locally:

   ```bash
   python3 scripts/validate.py
   python3 -m pytest -q
   ```

5. Commit `config/`, templates or scripts, tests, and the regenerated `output/shadowrocket.conf`.
6. Push to `main` and confirm the GitHub Actions run passes.
