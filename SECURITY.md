# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | Yes                |
| 1.x     | Security patches only |
| < 1.0   | No                 |

## Reporting a Vulnerability

If you find a security vulnerability, please report it privately:

1. Email the security team at security@astrovox.ai with:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix if available
   - Your contact information

2. Do not open a public issue for security vulnerabilities.

3. Do not disclose the vulnerability publicly until it has been fixed and announced.

4. We will acknowledge receipt within 5 business days and provide a timeline for a fix.

## Security Hardening

The platform includes the following security controls:

### Authentication & Authorization
- JWT authentication with RS256 (restricted algorithms)
- Row-level security (RLS) policies in Supabase
- Role-based access control (RBAC)
- Session management with secure cookies
- Password hashing with bcrypt/argon2

### Network Security
- Rate limiting per IP and per endpoint
- CORS configuration with whitelisted origins
- HTTPS enforcement with HSTS
- WebSocket secure connections (wss://)
- Private IP and SSRF protection

### Input Validation
- Request payload validation
- SQL injection prevention via ORM
- XSS protection with sanitized output
- CSRF token validation
- Content Security Policy headers

### Data Protection
- Secret scanning and scrubbing in logs
- Encryption at rest for sensitive data
- TLS 1.3 for data in transit
- PII detection and redaction
- Audit logging for sensitive operations

### Safe Execution
- Container sandbox for dynamic code execution
- Resource limits (CPU, memory, timeout)
- Network isolation for untrusted code
- Filesystem access restrictions

### Monitoring & Detection
- Security event logging
- Anomaly detection on auth patterns
- Brute force protection with exponential backoff
- Dependency vulnerability scanning

## Dependency Management

- Review `requirements.txt` and `package.json` before adding new dependencies.
- Prefer well-maintained libraries with recent security patches.
- Run `pip audit` and `npm audit` regularly in CI.
- Use Dependabot for automated dependency updates.
- Pin critical dependencies to known-good versions.

## Secrets Management

- Never commit secrets, API keys, or credentials to version control.
- Use environment variables or secret management services for all sensitive configuration.
- Rotate exposed keys immediately.
- Use `.env.example` to document required variables without values.
- Enable pre-commit hooks to scan for secrets (e.g., gitleaks).

## Incident Response

1. Identify and contain the incident
2. Assess impact and severity
3. Notify security team: security@astrovox.ai
4. Document findings and timeline
5. Implement remediation
6. Conduct post-incident review
7. Update security controls if needed

## Disclosure Policy

- We follow coordinated disclosure.
- We will publish a security advisory after the fix is available.
- Credit will be given to reporters who follow responsible disclosure.

## Security Checklist for Releases

- [ ] All dependencies audited: `npm audit` and `pip audit`
- [ ] No secrets in code or logs
- [ ] Security tests pass: `npm run test:security`
- [ ] Penetration testing completed for major releases
- [ ] Rate limiting configured appropriately
- [ ] CORS origins restricted to known domains
- [ ] Security headers validated
- [ ] Backup and restore procedures tested
