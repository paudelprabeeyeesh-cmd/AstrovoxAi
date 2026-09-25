# Access Control Policy

## Purpose
This document defines the access control policies and procedures for Astrovox AI to ensure compliance with SOC 2 Trust Services Criteria for Security (CC6.1).

## Scope
All systems, networks, and applications that store, process, or transmit customer data within the Astrovox AI environment.

## Identity and Access Management (IAM)
- **User Provisioning**: All user accounts are provisioned via automated identity management. Manual provisioning requires VP Engineering approval.
- **Least Privilege**: Users are granted the minimum level of access required to perform their job functions.
- **Role-Based Access Control (RBAC)**: Access is granted based on job role, not individual requests.
- **MFA Enforcement**: Multi-factor authentication is mandatory for all administrative and production access.

## Access Reviews
- Quarterly access reviews are conducted for all production systems.
- Access logs are retained for 365 days and reviewed monthly for anomalous activity.
- Terminated employees are deprovisioned within 24 hours via automated HRIS integration.

## Privileged Access Management
- Production root access requires Just-In-Time (JIT) elevation via PAM tool.
- All privileged sessions are recorded and stored for audit purposes.
- Passwords for service accounts are rotated every 90 days and stored in a secrets manager.

## Enforcement
Non-compliance with this policy is reported to the Security Committee and may result in access revocation.
