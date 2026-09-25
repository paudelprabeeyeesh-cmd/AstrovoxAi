# Audit Logging Policy

## Purpose
Establishes requirements for audit logging across Astrovox AI systems to meet SOC 2 CC7.1 and CC7.2 criteria.

## Logged Events
- Authentication and authorization events (success and failure)
- Data access and modification events
- System configuration changes
- Administrative actions
- API requests and responses
- Database queries for sensitive tables

## Log Requirements
- **Integrity**: Logs are protected from unauthorized modification using append-only storage and cryptographic hashing.
- **Completeness**: Logging must not be bypassed; application code must not swallow or suppress audit events.
- **Timeliness**: Logs are streamed to the SIEM within 60 seconds of event generation.
- **Retention**: Logs are retained for a minimum of 365 days in immutable storage.

## Centralized Log Management
- All application logs are forwarded to Prometheus + Loki for aggregation.
- Security-relevant logs are forwarded to the SIEM for alerting and correlation.
- Audit trails are stored in a separate, access-controlled index.

## Incident Detection
- Automated alerting rules are defined for critical security events.
- Alerts are triaged within 1 business day by the Security Operations team.
- All alert responses are documented in the incident response system.
