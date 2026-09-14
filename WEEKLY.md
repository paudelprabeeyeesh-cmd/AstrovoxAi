# Weekly Metrics Ritual

Every Sunday, 1 hour. Run these steps in order.

## 1. Pull Metrics (5 min)

```powershell
curl https://astrovoxai.onrender.com/metrics -H "Authorization: Bearer $ADMIN_TOKEN"
```

Record in METRICS.md:
- Total users
- Active users (7-day)
- Second-use rate
- Cost per user
- Revenue (MRR)
- Churn (canceled subscriptions)

## 2. Retention Analysis (10 min)

- % of users who called /solve twice within 7 days
- % of users who returned after day 7
- Cohort analysis: signup date vs. retention

## 3. Cost Analysis (10 min)

- Total API spend this week
- Cost per model (Groq vs. Gemini vs. Mistral)
- Cost per user
- Budget remaining for next week

## 4. Revenue Check (10 min)

- New subscriptions this week
- Cancellations
- MRR growth
- Conversion rate (free → paid)

## 5. Decision Matrix (15 min)

Pick ONE thing to KILL and ONE thing to DOUBLE DOWN on:

| Action | Type | Rationale | Owner |
|--------|------|-----------|-------|
| [Feature] | KILL | [Why it's not working] | [Name] |
| [Feature] | DOUBLE | [Why it's working] | [Name] |

## 6. Update METRICS.md

Append this week's snapshot:

```markdown
## Week of [DATE]

- Users: [X]
- Active: [Y]
- Second-use rate: [Z]%
- Cost/user: $[A]
- MRR: $[B]
- Churn: [C]%
- Kill: [Feature]
- Double: [Feature]
```

## 7. Share with Team

Post the metrics summary in the team channel. Highlight one win and one blocker.
