# Incident Response Plan

## Purpose
Defines the process for detecting, responding to, and recovering from security incidents to meet SOC 2 CC7.3, CC7.4, and CC7.5 criteria.

## Incident Classification
| Severity | Description | Response Time |
|----------|-------------|---------------|
| P1 - Critical | Data breach, service outage affecting all users | 15 minutes |
| P2 - High | Partial service outage, suspicious privilege escalation | 1 hour |
| P3 - Medium | Anomalous activity, failed compliance control | 4 hours |
| P4 - Low | Policy violation, low-severity vulnerability | 24 hours |

## Response Procedures
1. **Detection**: SIEM alerts, automated anomaly detection, user reports.
2. **Triage**: Security Operations validates and classifies the incident.
3. **Containment**: Isolate affected systems, revoke compromised credentials.
4. **Eradication**: Remove root cause, patch vulnerabilities, rotate secrets.
5. **Recovery**: Restore services from clean backups, verify integrity.
6. **Post-Mortem**: Document timeline, root cause, remediation steps, and preventive actions.

## Communication Plan
- **Internal**: Incident Commander notifies CTO and Legal within 30 minutes of P1 classification.
- **Customers**: Status page updated within 1 hour; detailed notification within 24 hours if data affected.
- **Regulators**: Breach notifications submitted per applicable state/federal laws (typically 72 hours).

## Evidence Preservation
- Forensic images of affected systems are created before remediation.
- All logs and artifacts are preserved in the incident locker.
- Chain of custody is documented for legal proceedings.

## Testing
Tabletop exercises are conducted quarterly; full-scale drills are conducted annually.
