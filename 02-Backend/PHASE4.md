# Phase 4: $100,000 → $500,000 MRR — Execution Plan

## Objective
Scale from 800 to 4,000 users in 180 days.

## Actionable Steps

### 1. Seed Round ($2-5M)
- Pitch deck: `docs/pitch_deck_seed.md`
- Target: AI-native VCs
- Valuation: $15-20M pre-money
- Use: Hire 5, scale infra, expand vertical

### 2. Scaling Team
- Hire: 2 engineers, 1 designer, 1 SDR, 1 CSM
- Onboarding: `docs/team_scaling.md`
- KPI: Team of 8 within 90 days

### 3. Self-Serve Enterprise Onboarding
- Use `enterprise_accounts.py`
- Automated provisioning
- KPI: 50% of enterprise signups self-serve

### 4. 2nd Vertical Expansion
- Use `verticals.py`
- Target: Healthcare or Legal
- KPI: 20% of new users from vertical 2

### 5. ISO 27001 Roadmap
- Docs: `docs/iso27001_roadmap.md`
- Tools: OneTrust, Vanta
- KPI: ISO 27001 ready in 180 days

## KPIs
- 4,000 users
- $500K MRR
- 30 enterprise contracts
- NPS >50

## Verification
```powershell
cd C:\AstrovoxAi\02-Backend
python -m pytest tests/ -q
```

## Commit
```
feat: add Phase 4 scaling - seed round docs, self-serve enterprise, vertical expansion, ISO 27001 roadmap
```
