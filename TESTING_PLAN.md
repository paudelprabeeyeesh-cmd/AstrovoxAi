# Testing Plan

## Strategy

Astrovox AI uses a comprehensive testing strategy covering unit, integration, E2E, security, performance, and AI quality tests.

## Test Pyramid

```
        /\
       /E2E\       10% - Critical user journeys
      /------\
     /Integr.\     20% - API contracts, component integration
    /----------\
   /Unit Tests \   70% - Component, hook, utility tests
  /--------------\
```

## Coverage Goals

- **Unit**: 90%+ line coverage
- **Integration**: 80%+ API coverage
- **E2E**: 100% critical path coverage
- **Security**: All OWASP Top 10
- **Performance**: P95 < 500ms
- **Accessibility**: 0 WCAG violations

## CI/CD Pipeline

1. Lint and typecheck
2. Unit tests
3. Integration tests
4. Build
5. E2E tests
6. Security scan
7. Performance benchmarks
8. Deploy

## Test Maintenance

- Update snapshots with `--update`
- Review and merge test PRs promptly
- Add tests for all new features
- Fix flaky tests immediately
- Weekly test health review
