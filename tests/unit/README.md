# Vitest Configuration

Unit tests use Vitest.

## Config Files

- `vitest.config.js` - Main config
- `vitest.unit.config.js` - Unit tests only
- `vitest.integration.config.js` - Integration tests

## Running Tests

```bash
# All tests
npm test

# Unit tests only
npm run test:unit

# Integration tests only
npm run test:integration

# With coverage
npm run test -- --coverage

# Watch mode
npm run test -- --watch
```

## Coverage

Coverage reports are generated in `coverage/` directory.

## CI

Tests run on every PR via GitHub Actions.
