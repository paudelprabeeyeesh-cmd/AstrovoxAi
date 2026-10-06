# Security Threat Model

This document records the primary threats Astrovox is designed to resist,
trust boundaries, and mitigation status.

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Client ↔ API | Untrusted internet traffic; requires TLS, auth, rate limiting. |
| API ↔ Model Providers | External network; validates responses, masks secrets. |
| API ↔ Database | Internal network; parameterized queries, RLS, least privilege. |
| API ↔ Cache | Internal network; key expiry, input validation. |
| Plugin Runtime ↔ Host | Untrusted plugin code; sandboxed execution, restricted builtins. |

## Top Threats

1. **Prompt injection through user input**
   Mitigation: input validation, safety layer, output filtering.

2. **Secret leakage via logs or errors**
   Mitigation: redaction filters, no raw token printing, audit review.

3. **Dependency compromise**
   Mitigation: `pip-audit`, `npm audit`, locked hashes, Trivy scanning.

4. **Insecure deserialization**
   Mitigation: prefer JSON/safetensors, limit `pickle` to local-only paths,
   bandit findings tracked and reviewed.

5. **Command injection in tool execution**
   Mitigation: avoid `shell=True`, validate commands, sandbox plugin code.

6. **Unauthorized data access**
   Mitigation: RBAC, RLS, signed URLs, audit logging, MFA for admin.

## Review Schedule

- Full threat model review: quarterly.
- Dependency audit: every PR via security-scan workflow.
- Penetration testing: annually or before major releases.
