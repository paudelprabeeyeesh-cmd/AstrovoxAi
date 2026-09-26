# Enterprise Setup Guide

This guide covers the complete enterprise feature set in AstrovoxAI, including SSO, LDAP, organization management, billing, subscriptions, usage quotas, API keys, team permissions, and compliance logs.

## SSO (Single Sign-On)

AstrovoxAI supports SAML 2.0 and OIDC for enterprise identity providers.

### Register a SAML Provider

```python
from app.enterprise.sso import enterprise_sso

enterprise_sso.register_saml(
    provider_name="Okta",
    metadata_url="https://dev-123.okta.com/metadata",
    entity_id="urn:astrovox",
)
```

### Register an OIDC Provider

```python
enterprise_sso.register_oidc(
    provider_name="Google",
    client_id="google-client-id",
    client_secret="google-client-secret",
    issuer="https://accounts.google.com",
)
```

### Authenticate via SSO

```python
result = enterprise_sso.authenticate(provider_key="oidc:Google", token="id-token-value")
print(result)
```

## LDAP

AstrovoxAI can authenticate users against an LDAP directory and sync group memberships.

### Configure LDAP

```python
from app.enterprise.ldap import LDAPClient, LDAPConfig

config = LDAPConfig(
    server="ldaps://ldap.example.com",
    bind_dn="cn=admin,dc=example,dc=com",
    base_dn="dc=example,dc=com",
    use_ssl=True,
    user_search_filter="(uid={username})",
)
client = LDAPClient(config)
```

### Authenticate a User

```python
user = client.authenticate(username="jdoe", password="secret")
print(user["groups"])
```

### Sync LDAP Groups to Organization

```python
groups = client.sync_groups(org_id="org-1")
print(groups)
```

## Organization Management

Create and manage organizations, workspaces, and memberships.

### Create an Organization

```python
from app.enterprise.organization_management import organization_manager

org = organization_manager.create_org(
    name="Acme Corp",
    owner_id="user-1",
    plan="enterprise",
    settings={"region": "us-east-1"},
)
print(org["id"], org["slug"])
```

### Invite a Member

```python
invite = organization_manager.invite_member(
    org_id=org["id"],
    email="alice@example.com",
    role="admin",
    invited_by="user-1",
)
print(invite["id"])
```

### List Organizations for a User

```python
orgs = organization_manager.list_orgs(user_id="user-1")
for o in orgs:
    print(o["name"], o["plan"])
```

## Billing

Create invoices and record payments.

### Create an Invoice

```python
from app.enterprise.billing import billing_manager

invoice = billing_manager.create_invoice(
    org_id="org-1",
    amount=499.0,
    currency="USD",
    line_items=[{"description": "Enterprise Plan", "amount": 499.0}],
)
print(invoice.id, invoice.status)
```

### Process a Payment

```python
payment = billing_manager.process_payment(invoice_id=invoice.id, payment_method="stripe")
print(payment["status"])
```

### Retrieve Invoice History

```python
history = billing_manager.get_invoice_history(org_id="org-1")
for inv in history:
    print(inv["id"], inv["status"], inv["amount"])
```

## Subscription Plans

Manage subscription lifecycles, upgrades, and cancellations.

### Create a Subscription

```python
from app.enterprise.subscriptions import subscription_manager

sub = subscription_manager.create_subscription(
    org_id="org-1",
    plan="enterprise",
    seats=50,
    interval="monthly",
)
print(sub.id, sub.status)
```

### Upgrade a Plan

```python
updated = subscription_manager.upgrade_plan(subscription_id=sub.id, new_plan="enterprise+")
print(updated.plan)
```

### Cancel a Subscription

```python
canceled = subscription_manager.cancel_subscription(subscription_id=sub.id, at_period_end=True)
print(canceled.cancel_at_period_end)
```

## Usage Quotas

Enforce per-organization usage limits with alerting thresholds.

### Set a Quota

```python
from app.enterprise.usage_quotas import quota_manager

quota = quota_manager.set_quota(
    org_id="org-1",
    resource_type="api_requests",
    limit=100000,
    period="monthly",
    alert_threshold=0.8,
)
print(quota.id, quota.limit_value)
```

### Check Quota Status

```python
status = quota_manager.check_quota(org_id="org-1", resource_type="api_requests")
print(status["used"], status["remaining"], status["allowed"])
```

### Enforce a Quota

```python
try:
    quota_manager.enforce_quota(org_id="org-1", resource_type="api_requests")
except PermissionError as exc:
    print(str(exc))
```

### Consume Quota

```python
consumption = quota_manager.consume(org_id="org-1", resource_type="api_requests", amount=10)
print(consumption["remaining"])
```

## API Keys

Generate, rotate, and revoke scoped API keys.

### Create an API Key

```python
from app.enterprise.api_keys import api_key_manager

key = api_key_manager.create_key(
    org_id="org-1",
    name="CI/CD Pipeline",
    scopes=["read", "execute"],
    expires_at="2027-01-01",
)
print(key["key_id"], key["secret"])
```

### Rotate a Key

```python
rotated = api_key_manager.rotate_key(key_id=key["key_id"])
print(rotated["new_secret"])
```

### Revoke a Key

```python
revoked = api_key_manager.revoke_key(key_id=key["key_id"])
print(revoked)
```

### Verify a Key

```python
verified = api_key_manager.verify_key(secret=key["secret"])
print(verified.id, verified.scopes)
```

## Team Permissions

Assign roles and enforce least-privilege access controls.

### Available Roles

- `owner` — full organization control
- `admin` — administration and member management
- `manager` — workspace creation and limited member management
- `member` — read/write access to workspaces
- `guest` — read-only access

### Assign a Role

```python
from app.enterprise.team_permissions import permission_manager

permission_manager.register_member(org_id="org-1", user_id="user-2", role="member")
result = permission_manager.assign_role(org_id="org-1", user_id="user-2", role="admin")
print(result)
```

### Check a Permission

```python
allowed = permission_manager.check_permission(
    user_id="user-2",
    org_id="org-1",
    permission="billing",
)
print(allowed)
```

### List All Permissions in an Organization

```python
perms = permission_manager.list_permissions(org_id="org-1")
for p in perms:
    print(p["user_id"], p["role"], p["permissions"])
```

## Compliance Logs

Record, query, and export immutable audit and compliance logs.

### Log a Compliance Event

```python
from app.enterprise.audit_log import compliance_logger

entry = compliance_logger.log(
    actor="admin",
    action="update_organization",
    resource="org:org-1",
    tenant_id="org-1",
    metadata={"field": "plan", "old": "free", "new": "enterprise"},
)
print(entry["timestamp"], entry["action"])
```

### Query Logs

```python
logs = compliance_logger.query(
    actor="admin",
    action="update_organization",
    tenant_id="org-1",
)
for log in logs:
    print(log)
```

### Export Logs

```python
exported = compliance_logger.export(fmt="json")
print(exported)
```

### Generate a Compliance Report

```python
from app.enterprise.compliance import compliance_generator
from datetime import datetime, timezone

report = compliance_generator.generate(
    tenant_id="org-1",
    framework="SOC2",
    start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
    end_date=datetime(2026, 9, 26, tzinfo=timezone.utc),
)
print(report.report_id, report.summary)

exported = compliance_generator.export_report(report=report, fmt="json")
print(exported)
```
