# Safety Incident Runbook

## Overview
This runbook guides responders through a safety incident involving harmful content, jailbreaks, PII leaks, or model misbehavior.

## Detection
- Alert fired in Prometheus (`SafetyViolationSpike`)
- Human moderator flags content in the admin console
- Automated safety module raises `SafetyAlert` event

## Triage
1. Acknowledge alert in PagerDuty / Slack #safety-incidents.
2. Identify the affected model, endpoint, and user/org.
3. Check `app.safety.audit` and `compliance.compliance_logger` for the event timeline.
4. Determine severity:
   - **Critical**: active data leak, ongoing jailbreak exploitation, self-harm content.
   - **High**: PII exposure, hate speech, violent content.
   - **Medium**: bias flags, excessive refusal, moderate policy violations.

## Response
### Immediate Actions
- If critical, enable **emergency block** on the affected model/endpoint via admin API.
- Quarantine the offending prompt/response pair.
- Notify the org admin and the affected user.

### Investigation
- Pull logs from `app.safety.jailbreak`, `app.safety.moderation_pipeline`, `app.safety.data_leak_prevention`.
- Run the `EvaluationHarness` against the model with the offending prompt to reproduce.
- Check for prompt injection vectors using `app.safety.injection_defense`.

### Remediation
- Update blocklists and classifiers.
- If model-level issue, switch traffic to fallback model.
- If system issue, patch and deploy.

## Communication
- Post status updates every 15 minutes in #safety-incidents.
- For critical incidents, email `safety@astrovox.ai` and `legal@astrovox.ai`.
- Update status page if user-facing impact is confirmed.

## Post-Mortem
- Document timeline, root cause, and remediation steps within 48 hours.
- Update runbooks and classifier thresholds.
- Schedule review with Safety and Engineering leads.
