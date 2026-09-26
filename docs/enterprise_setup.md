# Enterprise Setup Guide

## SSO and LDAP

AstrovoxAI supports OIDC, SAML, and LDAP for enterprise identity.

### OIDC / SAML
Configure SSO via the enterprise admin panel or API:
```python
from app.sso import sso_service
provider = sso_service.register_provider(org_id="...", provider_type="oidc", config={...})
```

### LDAP
Configure LDAP in `02-Backend/app/enterprise/ldap.py`:
```python
from app.enterprise.ldap import LDAPClient, LDAPConfig

config = LDAPConfig(server="ldaps://ldap.example.com", bind_dn="cn=admin,dc=example,dc=com", base_dn="dc=example,dc=com")
client = LDAPClient(config)
user = client.authenticate(username="jdoe", password="secret")
print(user["groups"])
```

## Organization Management

Create organizations and manage members:
```python
from app.enterprise.organization_management import organization_manager

org = organization_manager.create_org(name="Acme Corp", owner_id="user-1", plan="team")
invite = organization_manager.invite_member(org_id=org["id"], email="alice@example.com", role="member")
```

## Billing and Subscriptions

Create invoices and manage subscriptions:
```python
from app.enterprise.billing import billing_manager
invoice = billing_manager.create_invoice(org_id="org-1", amount=99.0, currency="USD")

from app.enterprise.subscriptions import subscription_manager
sub = subscription_manager.create_subscription(org_id="org-1", plan="team", seats=10)
```

## Usage Quotas

Set and enforce quotas:
```python
from app.enterprise.usage_quotas import quota_manager

quota_manager.set_quota(org_id="org-1", resource_type="api_requests", limit=10000, period="monthly")
quota_manager.enforce_quota(org_id="org-1", resource_type="api_requests")
```

## API Keys

Manage scoped API keys:
```python
from app.enterprise.api_keys import api_key_manager

key = api_key_manager.create_key(org_id="org-1", name="CI/CD", scopes=["read", "execute"])
print(key["secret"])  # Save this securely
```

## Team Permissions

Assign roles and check permissions:
```python
from app.enterprise.team_permissions import permission_manager

permission_manager.assign_role(org_id="org-1", user_id="user-2", role="admin")
allowed = permission_manager.check_permission(user_id="user-2", org_id="org-1", permission="billing")
```
