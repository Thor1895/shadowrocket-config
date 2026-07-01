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
- OpenAI candidates are limited to Japan, Singapore, and United States nodes.
- Xiaohongshu routes through `PROXY`.
- Alipay, WeChat, Amap, Meituan, Ele.me, and bank domains route through `DIRECT`.

## Daily Maintenance

1. Update nodes in `config/nodes.yaml`.
2. Update routing rules in `config/rules.yaml`.
3. Regenerate the output:

   ```bash
   python3 build.py
   ```

4. Validate locally:

   ```bash
   python3 scripts/validate.py
   python3 -m pytest -q
   ```

5. Commit `config/`, templates or scripts, tests, and the regenerated `output/shadowrocket.conf`.
6. Push to `main` and confirm the GitHub Actions run passes.
