# Enterprise Platform

AstrovoxAI Enterprise provides a multi-tenant SaaS platform with advanced security, compliance, billing, and team collaboration features.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ENTERPRISE PLATFORM                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Tenant     │    │   Identity   │    │   Access Control     │  │
│  │   Manager    │    │   Provider   │    │   (RBAC + ABAC)      │  │
│  └──────┬───────┘    └──────────────┘    └──────────┬───────────┘  │
│         │                                            │               │
│  ┌──────▼────────────────────────────────────────────▼───────────┐  │
│  │                    Billing Engine                                │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │  │
│  │  │  Subscription│  │  Usage       │  │  Invoice &           │  │  │
│  │  │  Manager     │  │  Metering    │  │  Payment             │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Audit      │    │   Compliance │    │   Security           │  │
│  │   Logger     │    │   Manager    │    │   Scanner            │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Multi-Tenancy

### Tenant Isolation

Each tenant operates in a fully isolated environment:

```python
from ASTROVOX_AI.backend.app.enterprise.tenant_manager import TenantManager

tenant_manager = TenantManager()

# Create tenant
tenant = tenant_manager.create_tenant(
    name="Acme Corp",
    domain="acme.astrovox.ai",
    plan="enterprise",
    admin_email="admin@acme.com"
)

# Switch tenant context
tenant_manager.set_tenant_context(tenant.id)

# All operations are scoped to this tenant
conversations = get_conversations()  # Only Acme Corp's data
```

### Isolation Mechanisms

| Mechanism | Implementation |
|-----------|----------------|
| Database | Separate schemas per tenant |
| Storage | S3 prefix isolation |
| Cache | Redis key namespacing |
| API | Tenant ID in JWT claims |
| Rate Limits | Per-tenant quotas |
| Domain | Subdomain routing |

### Resource Quotas

```python
tenant.set_quota('api_calls_per_day', 100000)
tenant.set_quota('storage_gb', 500)
tenant.set_quota('users', 100)
tenant.set_quota('ai_requests_per_day', 50000)
```

## SSO & Identity

### SAML 2.0 Configuration

```python
from ASTROVOX_AI.backend.app.enterprise.sso_router import SAMLConfig

saml_config = SAMLConfig(
    sp_entity_id="astrovox",
    idp_entity_id="company-idp",
    idp_sso_url="https://login.company.com/sso",
    idp_x509_cert="-----BEGIN CERTIFICATE-----...",
    sp_private_key="-----BEGIN PRIVATE KEY-----..."
)
```

### OIDC Configuration

```python
from ASTROVOX_AI.backend.app.enterprise.sso_router import OIDCConfig

oidc_config = OIDCConfig(
    issuer="https://login.company.com",
    client_id="astrovox-client",
    client_secret="secret",
    scopes=["openid", "profile", "email"]
)
```

### Supported Providers

| Provider | Protocol | Features |
|----------|----------|----------|
| Okta | SAML 2.0, OIDC | JIT provisioning, group sync |
| Azure AD | SAML 2.0, OIDC | SCIM, conditional access |
| Google Workspace | OIDC | Domain-wide delegation |
| Auth0 | SAML 2.0, OIDC | Rules, hooks |
| OneLogin | SAML 2.0 | MFA enforcement |

### SCIM Provisioning

```python
# Automatic user lifecycle management
@app.post("/api/v1/enterprise/scim/users")
async def scim_create_user(request: Request):
    user_data = await request.json()
    user = enterprise.create_user(
        email=user_data["emails"][0]["value"],
        name=user_data["name"]["givenName"],
        external_id=user_data.get("externalId")
    )
    return user.to_scim_dict()
```

## RBAC & ABAC

### Role-Based Access Control

```python
from ASTROVOX_AI.backend.app.security.rbac import RBACManager, Role

rbac = RBACManager()

# Define roles
rbac.define_role(Role.USER, permissions=[
    "chat:create", "chat:read", "memory:write"
])

rbac.define_role(Role.DEVELOPER, permissions=[
    "chat:create", "chat:read", "chat:write",
    "memory:write", "api:access", "logs:read"
])

rbac.define_role(Role.ADMIN, permissions=[
    "*"  # All permissions
])

# Check permissions
if rbac.check(user, "chat:delete", resource):
    delete_conversation(resource)
```

### Attribute-Based Access Control

```python
from ASTROVOX_AI.backend.app.enterprise.abac_router import ABACPolicy

policy = ABACPolicy(
    rules=[
        {
            "effect": "allow",
            "actions": ["chat:read"],
            "conditions": {
                "resource.owner_id": "${user.id}",
                "request.time": {"gte": "09:00", "lte": "17:00"}
            }
        }
    ]
)
```

## Billing Engine

### Subscriptions

```python
from ASTROVOX_AI.backend.app.enterprise.billing_router import BillingEngine

billing = BillingEngine()

# Plans
billing.define_plan("free", {
    "monthly_price": 0,
    "ai_requests": 100,
    "storage_gb": 1,
    "users": 1
})

billing.define_plan("pro", {
    "monthly_price": 29,
    "ai_requests": 10000,
    "storage_gb": 50,
    "users": 10
})

billing.define_plan("enterprise", {
    "monthly_price": 299,
    "ai_requests": -1,  # Unlimited
    "storage_gb": -1,
    "users": -1
})
```

### Usage Metering

```python
from ASTROVOX_AI.backend.app.enterprise.billing_router import UsageMeter

meter = UsageMeter()

# Record usage events
meter.record(
    tenant_id=tenant.id,
    metric="ai_requests",
    quantity=1,
    metadata={"model": "gpt-4", "tokens": 150}
)

meter.record(
    tenant_id=tenant.id,
    metric="storage_bytes",
    quantity=1024 * 1024,  # 1MB
    metadata={"type": "file_upload"}
)

# Get current usage
usage = meter.get_usage(
    tenant_id=tenant.id,
    period="current_month"
)
```

### Invoicing

```python
from ASTROVOX_AI.backend.app.enterprise.billing_router import InvoiceGenerator

generator = InvoiceGenerator()

# Generate monthly invoice
invoice = generator.generate(
    tenant_id=tenant.id,
    period="2024-01",
    line_items=[
        {"description": "Pro Plan", "amount": 2900},
        {"description": "Overage (100 requests)", "amount": 200}
    ]
)

# Export to PDF
pdf = invoice.to_pdf()
```

### Tax Engine

```python
from ASTROVOX_AI.backend.app.enterprise.billing_router import TaxEngine

tax = TaxEngine()

# Calculate tax based on customer location
tax_amount = tax.calculate(
    amount=29.00,
    country="US",
    state="CA",
    postal_code="90210"
)
```

### Coupons & Referrals

```python
from ASTROVOX_AI.backend.app.enterprise.billing_router import CouponManager

coupons = CouponManager()

# Create coupon
coupon = coupons.create(
    code="SUMMER2024",
    discount_type="percentage",
    value=20,
    valid_from="2024-06-01",
    valid_until="2024-08-31",
    max_uses=1000
)

# Apply coupon
discount = coupons.apply(
    tenant_id=tenant.id,
    code="SUMMER2024",
    amount=29.00
)
```

## Compliance

### SOC 2 Type II

- Immutable audit trail for all actions
- Access control verification
- Change management tracking
- Incident response logging

### GDPR

```python
from ASTROVOX_AI.backend.app.enterprise.compliance import GDPRCompliance

gdpr = GDPRCompliance()

# Data export
export = gdpr.export_user_data(user_id)

# Right to be forgotten
gdpr.delete_user_data(user_id)
```

### Audit Logging

```python
from ASTROVOX_AI.backend.app.enterprise.audit import AuditLogger

logger = AuditLogger()

# Log all mutations
logger.log(
    actor=user.id,
    action="conversation.deleted",
    resource=f"conversation/{conv_id}",
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)
```

## SLA & Support

### Uptime Monitoring

```python
from ASTROVOX_AI.backend.app.enterprise.sla import SLAMonitor

sla = SLAMonitor(target_uptime=99.9)

# Track uptime
sla.record_uptime_check()
sla.record_downtime(start, end, reason)

# Calculate SLA
current_sla = sla.calculate_sla(period="current_month")
```

### Support Tiers

| Tier | Response Time | Channels |
|------|---------------|----------|
| Free | Best effort | Community |
| Pro | 24 hours | Email |
| Business | 4 hours | Email + Chat |
| Enterprise | 1 hour | Dedicated support, Phone |

## Team Management

```python
from ASTROVOX_AI.backend.app.enterprise.team_router import TeamManager

team = TeamManager(tenant_id=tenant.id)

# Create team
team.create(name="Engineering", description="Engineering team")

# Add members
team.add_member(
    user_id=user.id,
    role="admin",
    permissions=["*"]
)

team.add_member(
    user_id=user2.id,
    role="member",
    permissions=["chat:read", "chat:write"]
)

# Shared resources
team.share_conversation(conversation_id, team_id="Engineering")
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/enterprise/sso/saml` | SAML SSO login |
| POST | `/api/v1/enterprise/sso/oidc` | OIDC SSO login |
| GET | `/api/v1/enterprise/team/members` | List team members |
| POST | `/api/v1/enterprise/team/members` | Add team member |
| GET | `/api/v1/enterprise/billing/usage` | Get usage metrics |
| POST | `/api/v1/enterprise/billing/subscribe` | Create subscription |
| POST | `/api/v1/enterprise/billing/coupons/apply` | Apply coupon |
| GET | `/api/v1/enterprise/audit/logs` | Get audit logs |
| POST | `/api/v1/enterprise/compliance/export` | GDPR data export |
| DELETE | `/api/v1/enterprise/compliance/user/{id}` | Delete user data |
