# Security Policy

## Supported Versions

| Version | Supported | Security Updates |
|---------|-----------|------------------|
| 2.x     | Yes       | Active           |
| 1.x     | No        | None             |

## Reporting a Vulnerability

**DO NOT** open a public GitHub issue for security vulnerabilities.

### Reporting Process

1. Email: security@astrovox.ai
2. Subject: `[SECURITY] <brief description>`
3. Include:
   - Affected version(s)
   - Reproduction steps
   - Proof of concept (if safe to share)
   - Suggested fix (if any)

### Response Timeline

- **24 hours:** Acknowledgment
- **72 hours:** Triage and severity assessment
- **7 days:** Initial fix or mitigation plan
- **30 days:** Patch release (critical: 7 days)

## Security Measures

### Authentication

- JWT tokens with 256-bit secret minimum
- HTTP-only, secure cookies for web clients
- Refresh token rotation
- Email verification required before login

### Authorization

- Role-based access control (RBAC)
- Resource-level permissions
- API key scoping for integrations

### Data Protection

- TLS 1.3 for all external traffic
- AES-256 encryption at rest for sensitive fields
- Secrets managed via Kubernetes Secrets / external secrets manager
- No hardcoded credentials in source code

### Input Validation

- Pydantic models enforce schema constraints
- SQL injection prevention via parameterized queries
- XSS prevention via Content-Security-Policy headers
- CSRF protection for state-changing operations

### Rate Limiting

- Per-IP rate limiting on all public endpoints
- Failed-attempt lockout: 5 failures / 15 minutes
- Configurable limits via environment variables

### Logging

- Structured JSON logs with request IDs
- Sensitive data redacted from logs
- Immutable audit log for compliance
- No secrets in log output

### Dependency Security

- Automated vulnerability scanning in CI
- `pip-audit` and `npm audit` on every PR
- Dependabot enabled for auto-updates
- SBOM generated for all releases

## Secure Development

### Requirements

- All PRs require review from at least one maintainer
- CI must pass (lint, tests, security scan)
- No secrets in git history
- New dependencies require security review

### Code Review Checklist

- [ ] No hardcoded secrets or API keys
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive info
- [ ] SQL queries are parameterized
- [ ] New dependencies are approved
- [ ] Tests cover security-critical paths

## Incident Response

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| P0 | Active exploitation | 1 hour | RCE, data breach |
| P1 | High impact | 4 hours | Auth bypass, data leak |
| P2 | Medium impact | 24 hours | XSS, CSRF |
| P3 | Low impact | 7 days | Information disclosure |

### Response Process

1. **Contain:** Isolate affected systems
2. **Investigate:** Identify root cause and blast radius
3. **Remediate:** Deploy fix or mitigation
4. **Communicate:** Notify affected users if required
5. **Post-mortem:** Document and prevent recurrence

## Compliance

- SOC 2 Type II (in progress)
- GDPR compliant (data export, deletion)
- CCPA compliant (data portability)
- Annual penetration testing

## Third-Party Security

### LLM Providers

- API keys rotated quarterly
- Minimum necessary data sent to providers
- Output filtered for PII before external processing

### Infrastructure

- AWS/GCP security best practices
- Network policies restrict pod-to-pod communication
- Regular backup verification
- Disaster recovery tested quarterly

## Security Contacts

- **Security Team:** security@astrovox.ai
- **PGP Key:** Available at https://astrovox.ai/pgp-key.asc
- **Bug Bounty:** Coming soon
