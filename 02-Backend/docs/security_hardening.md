# Security Hardening

## Principles

- **Defense in depth**: Apply controls at the network, host, application, and data layers.
- **Least privilege**: Services and users get only the permissions they need.
- **Secure by default**: Deny all, then explicitly allow.

## Application Security

- Run containers as non-root `appuser` (`Dockerfile`).
- Set security headers via `app/security_headers.py` (CSP, HSTS, X-Frame-Options, etc.).
- Validate and sanitize all user input; use Pydantic models for request validation.
- Use parameterized queries / ORM to prevent SQL injection.
- Hash passwords with `bcrypt` or `argon2`; never store plaintext secrets.

## Authentication & Authorization

- Use short-lived JWTs with strong `JWT_SECRET_KEY` (256-bit minimum); rotate quarterly.
- Store secrets in a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault); never in code or environment variables in production.
- Enforce MFA for admin and privileged accounts.
- Apply rate limiting per user/IP to prevent brute-force and DoS.

## Transport Security

- Enforce HTTPS with valid TLS certificates (Let's Encrypt / internal CA).
- Set `HSTS` with `max-age >= 31536000` and `includeSubDomains`.
- Disable weak cipher suites; prefer TLS 1.3.

## Data Protection

- Encrypt data at rest (Postgres, Redis, Neo4j volumes).
- Redact PII at ingestion; never log raw PII, secrets, or tokens.
- Use `pgcrypto` or application-level encryption for sensitive fields.

## Infrastructure

- Run services in a private network; expose only necessary ports.
- Use network policies to restrict pod-to-pod communication (Kubernetes).
- Scan images for vulnerabilities (`docker scan`, Trivy, Grype) in CI.
- Keep base images and dependencies up to date; automate dependency reviews (Dependabot, Renovate).

## Monitoring & Incident Response

- Log security events: failed logins, permission denials, suspicious activity.
- Alert on anomaly patterns; integrate with incident runbook (`incident_runbook.md`).
- Conduct regular threat modeling and penetration testing.

## Compliance

- Align with SOC 2 Type I controls (`soc2_type1.md`) and ISO 27001 roadmap (`iso27001_roadmap.md`).
- Maintain audit logs for access, changes, and security events.
