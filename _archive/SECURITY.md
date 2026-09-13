# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | Yes                |
| < 1.0   | No                 |

## Reporting a Vulnerability

If you find a security vulnerability, please report it privately:

1. Email the maintainers at security@astrovox.ai with:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix if available

2. Do not open a public issue for security vulnerabilities.

3. We will acknowledge receipt within 5 business days and provide a timeline for a fix.

## Security Hardening

The backend includes the following security controls:

- JWT authentication with restricted algorithms
- Row-level security policies in Supabase
- Rate limiting per IP and per endpoint
- Input validation and sanitization
- Secret scanning and scrubbing in logs
- Private IP and SSRF protection
- Safe execution sandbox for dynamic code
- Audit logging for sensitive operations

## Dependency Management

- Review `requirements.txt` and `package.json` before adding new dependencies.
- Prefer well-maintained libraries with recent security patches.
- Run `pip audit` and `npm audit` regularly.

## Secrets Management

- Never commit secrets, API keys, or credentials.
- Use environment variables for all sensitive configuration.
- Rotate exposed keys immediately.

## Disclosure Policy

- We follow coordinated disclosure.
- We will publish a security advisory after the fix is available.
