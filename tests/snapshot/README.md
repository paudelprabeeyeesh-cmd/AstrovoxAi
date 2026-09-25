# Snapshot Tests

Snapshot tests ensure UI consistency across releases.

## Running Snapshot Tests

```bash
npm run test:snapshot
```

## Updating Snapshots

```bash
npm run test:snapshot -- --update
```

## Snapshot Files

- `src/components/chat/__snapshots__/ChatInterface.snap`
- `src/components/chat/__snapshots__/StreamingMessage.snap`
- `src/components/ui/__snapshots__/ThemeEngine.snap`

## CI Integration

Snapshots are validated in CI. If snapshots change, the CI will fail and you need to review and update them.
