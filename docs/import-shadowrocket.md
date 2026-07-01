# Import Shadowrocket Config

Use the GitHub Release URL to import the generated configuration into Shadowrocket:

```text
https://github.com/Thor1895/shadowrocket-config/releases/latest/download/shadowrocket.conf
```

## Steps

1. Open Shadowrocket on iOS.
2. Tap the add button.
3. Choose the option to add a remote configuration or subscribe by URL.
4. Paste the release URL:

   ```text
   https://github.com/Thor1895/shadowrocket-config/releases/latest/download/shadowrocket.conf
   ```

5. Save the subscription and update it in Shadowrocket.

After each update to `main`, GitHub Actions rebuilds the config and updates the `latest` release asset. The URL stays the same, so Shadowrocket can keep using it as a permanent subscription endpoint.

The legacy raw URL is still available when needed:

```text
https://raw.githubusercontent.com/Thor1895/shadowrocket-config/main/output/shadowrocket.conf
```
