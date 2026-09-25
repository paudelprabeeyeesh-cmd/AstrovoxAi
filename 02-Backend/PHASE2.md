# Phase 2: $5,000 → $25,000 MRR — Execution Plan

## Objective
Scale from 50 to 200 paying users in 90 days.

## Actionable Steps

### 1. First Contractor (Support)
- Hire VA for $5/hr, 20 hrs/week
- Script: `scripts/support_handoff.py`
- KPI: <4 hour response time

### 2. Managed Postgres/Redis
- Migrate from SQLite to Supabase
- Update `database.py` to use Supabase client
- Update `docker-compose.yml` to remove Redis, add Supabase
- KPI: 99.9% uptime

### 3. Paid Ads ($500/mo budget)
- Use `campaigns.py` to track
- Platforms: Google Ads, LinkedIn, X
- Target: "AI API", "AI SaaS"
- KPI: CAC <$100, LTV/CAC >3

### 4. $99 Usage-Based Tier
- Add to `subscriptions.py`
- Stripe price ID: `price_usage_99`
- Limits: 10,000 requests/month
- KPI: 20% of users on $99 tier

## KPIs
- 200 paying users
- $25K MRR
- CAC <$100

## Verification
```powershell
cd C:\AstrovoxAi\02-Backend
python -m pytest tests/ -q
```

## Commit
```
feat: add Phase 2 scaling - managed infra, $99 tier, ad tracking, support scripts
```
