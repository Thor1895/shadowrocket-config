# shadowrocket-config

Python + YAML + Jinja2 based Shadowrocket configuration generator.

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

## Routing Policy

- OpenAI, Gemini, and Claude each have an independent policy group and do not use `PROXY`.
- OpenAI candidates are limited to Japan, Singapore, and United States nodes.
- Xiaohongshu routes through `PROXY`.
- Alipay, WeChat, Amap, Meituan, Ele.me, and bank domains route through `DIRECT`.
