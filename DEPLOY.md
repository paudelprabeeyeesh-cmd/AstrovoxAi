# DEPLOY.md

## Render Free Tier

1. Push code to GitHub.
2. Go to https://dashboard.render.com/blueprint/new
3. Connect repo `paudelprabeeyeesh-cmd/AstrovoxAi`
4. Set `Dockerfile` as build command.
5. Add env vars from `.env.example`.
6. Click Create. URL will be `https://astrovox-api.onrender.com`.

## Verify
```bash
curl https://astrovox-api.onrender.com/health
curl https://astrovox-api.onrender.com/metrics
```
