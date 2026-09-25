# DEPLOY.md

## Vercel (Next.js)

1. Push code to GitHub.
2. Go to https://vercel.com/new
3. Import repo `paudelprabeeyeesh-cmd/AstrovoxAi`
4. Set **Root Directory** to `apps/web` (critical — root has Python files that misdetect the project as FastAPI)
5. Add env vars from `apps/web/.env.local` or `.env.example`
6. Click **Deploy**. URL will be `https://astrovox-ai-web.vercel.app`.

## Render (Backend / API)

1. Go to https://dashboard.render.com/blueprint/new
2. Connect repo `paudelprabeeyeesh-cmd/AstrovoxAi`
3. Set `Dockerfile` as build command.
4. Add env vars from `.env.example`.
5. Click Create. URL will be `https://astrovox-api.onrender.com`.

## Verify
```bash
curl https://astrovox-api.onrender.com/health
curl https://astrovox-api.onrender.com/metrics
```
