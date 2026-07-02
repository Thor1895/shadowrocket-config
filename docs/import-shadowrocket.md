# Import Shadowrocket Config

This project now uses private local builds. Generate the config locally:

```bash
export SUBSCRIBE_URL='你的订阅链接'
SKIP_SYNC_GUARD=1 python3 build.py
```

## Steps

1. Open Shadowrocket on iOS.
2. Tap the add button.
3. Choose the option to add a remote configuration or subscribe by URL.
4. Import the local `output/shadowrocket.conf` file through your preferred private transfer method.
5. Save the configuration and update it in Shadowrocket.

Do not upload `output/shadowrocket.conf` to a public GitHub raw URL or Release asset. It contains subscription nodes and credentials.
