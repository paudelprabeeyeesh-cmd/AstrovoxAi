# Security Tests

## Overview

Security tests verify that the application and client SDK resist common attack vectors.

## Running

```bash
npm run test:security
npm run test:owasp
```

## Coverage

- OWASP Top 10 checks
- XSS prevention
- SQL injection prevention
- Authorization header validation
- HTTPS enforcement
- Sensitive data handling
- CSRF protection

## Adding New Tests

Add new test cases to `auth.test.ts` or `owasp-zap.test.ts`.