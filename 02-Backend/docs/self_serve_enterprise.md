# Self-Serve Enterprise Onboarding

## Flow

1. User visits astrovox.ai/enterprise
2. Fills out form: company, email, employees
3. Creates account
4. Auto-provisions team workspace
5. Sends welcome email with SSO setup
6. 14-day free trial
7. Onboarding call scheduled (Day 3)

## Technical Implementation

```python
# enterprise_accounts.py
def create_enterprise_account(company: str, contact_email: str) -> dict:
    account_id = str(uuid.uuid4())
    team_id = create_team(account_id, company)
    send_welcome_email(contact_email, team_id)
    schedule_onboarding_call(contact_email)
    return {"account_id": account_id, "team_id": team_id}
```

## Requirements
- SSO (Google, Okta, Azure AD)
- Audit logs
- Custom SLA
- Dedicated support

## Conversion Rate Target
- 50% of signups convert to paid within 14 days
