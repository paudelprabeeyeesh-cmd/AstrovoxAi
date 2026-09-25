# Auto-Update Channel

Astrovox desktop apps use Tauri's built-in updater.

## Update Channels

### Stable
- Production-ready releases
- Thoroughly tested
- Recommended for most users
- Updates every 2-4 weeks

### Beta
- New features and improvements
- Some bugs expected
- For early adopters
- Updates every week

### Nightly
- Latest development builds
- May be unstable
- For testing only
- Daily updates

## Configuration

```json
{
  "updater": {
    "endpoints": [
      "https://releases.astrovox.ai/stable/latest.json",
      "https://releases.astrovox.ai/beta/latest.json",
      "https://releases.astrovox.ai/nightly/latest.json"
    ],
    "dialog": true,
    "pubkey": "dW50cnVzdGVkIGNvbW1lbnQ6..."
  }
}
```

## Release Process

1. Build and test
2. Sign with release key
3. Upload to release server
4. Notify users via in-app notification
5. Update changelog and docs
