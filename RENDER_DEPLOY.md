# Render Deployment — Exact Steps

## Prerequisites
- Code pushed to GitHub (already done)
- Render account (free tier)

## Steps

1. Go to https://dashboard.render.com/blueprint/new
2. Click "Connect a repository"
3. Select `paudelprabeeyeesh-cmd/AstrovoxAi`
4. Render auto-detects `render.yaml`
5. Click "Apply" or "Create"
6. Wait 3-5 minutes for build
7. Add environment variable:
   - Key: `OPENAI_API_KEY`
   - Value: your actual OpenAI key
8. Click "Save" and wait for redeploy

## Verify Deployment

```powershell
# Health check
curl https://astrovox-api.onrender.com/health

# Metrics
curl https://astrovox-api.onrender.com/metrics

# Solve endpoint
curl -X POST https://astrovox-api.onrender.com/solve -H "Authorization: Bearer user-123" -H "Content-Type: application/json" -d "{\"text\": \"hello world\", \"user_id\": \"user123\"}"
```

## Custom Domain (optional)
- In Render dashboard: Settings > Custom Domains
- Add your domain
- Update DNS CNAME to `astrovox-api.onrender.com`

## Monitoring
- Render free tier sleeps after 15 min inactivity
- First request after sleep takes ~30 seconds
- Upgrade to paid tier ($7/mo) for always-on

## Troubleshooting
- If 502: check Render logs in dashboard
- If 500: check OPENAI_API_KEY is set
- If slow: first request cold-starts the container
