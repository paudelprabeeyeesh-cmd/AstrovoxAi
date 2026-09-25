# Release Strategy

## Versioning
- Semantic versioning: MAJOR.MINOR.PATCH
- Current version: 1.0.0

## Release Types

### Patch Release
- Bug fixes only
- No API changes
- Deploy anytime
- Rollback: automatic on SLO violation

### Minor Release
- New features, backward compatible
- Deploy during business hours
- Canary: 10% → 50% → 100%
- Rollback: manual or automatic

### Major Release
- Breaking changes
- Requires migration guide
- Deploy during maintenance window
- Blue-green deployment
- Rollback: blue-green switch

## Process
1. Create release branch: `release/v1.x`
2. Update changelog
3. Run full test suite
4. Security scan
5. Deploy to staging
6. QA sign-off
7. Deploy to production
8. Monitor for 24 hours
9. Tag release
10. Merge to main

## Hotfix Process
1. Branch from main: `hotfix/issue-123`
2. Fix and test
3. Deploy directly to production
4. Back-merge to main and develop
