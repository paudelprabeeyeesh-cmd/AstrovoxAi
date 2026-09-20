# AstrovoxAI  Deployment Playbook

## Pre-Flight Checklist
- [ ] GitHub repo is up to date: https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi
- [ ] All tests pass locally
- [ ] No hardcoded secrets in code
- [ ] .env.example is up to date

## Backend Deployment (Render)

### Step 1: Create PostgreSQL Database
1. Go to https://dashboard.render.com
2. Click "New +" ? "PostgreSQL"
3. Name: `astrovox-db`
4. Plan: Free (or Standard for production)
5. Click "Create"
6. Copy the `Internal Connection URL` (format: `postgresql://user:pass@host:5432/db`)

### Step 2: Create Redis Database
1. Click "New +" ? "Redis"
2. Name: `astrovox-redis`
3. Plan: Free
4. Copy the `Connection URL`

### Step 3: Deploy Backend Service
1. Click "New +" ? "Web Service"
2. Connect GitHub repo: `paudelprabeeyeesh-cmd/AstrovoxAi`
3. Configure:
   - **Name**: `astrovox-api`
   - **Runtime**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Docker Context**: `.`
   - **Plan**: Standard ($7/mo)
   - **Region**: Ohio (or closest to users)
4. Add Environment Variables:
   ```
   DATABASE_URL=<from PostgreSQL step>
   REDIS_URL=<from Redis step>
   OPENAI_API_KEY=<your key>
   GROQ_API_KEY=<your key>
   GEMINI_API_KEY=<your key>
   MISTRAL_API_KEY=<your key>
   HF_API_KEY=<your key>
   STRIPE_SECRET_KEY=<your key>
   STRIPE_WEBHOOK_SECRET=<your secret>
   JWT_SECRET_KEY=<generate 32+ char random string>
   ALLOWED_ORIGINS=https://astrovox.ai,https://www.astrovox.ai,https://astrovox-api.onrender.com
   PYTHON_VERSION=3.12.0
   ```
5. Click "Create Web Service"
6. Wait 5-10 minutes for build
7. Test: `curl https://astrovox-api.onrender.com/health`

### Step 4: Configure Stripe Webhooks
1. Go to https://dashboard.stripe.com/webhooks
2. Click "Add endpoint"
3. URL: `https://astrovox-api.onrender.com/webhooks/stripe`
4. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copy webhook secret to Render env vars

### Step 5: Run Database Migrations
1. In Render, go to `astrovox-api` ? "Shell"
2. Run: `cd 02-Backend && alembic upgrade head`

## Frontend Deployment (Vercel)

### Step 1: Prepare Frontend
1. Update `apps/web/.env.local`:
   ```
   NEXT_PUBLIC_API_URL=https://astrovox-api.onrender.com
   NEXTAUTH_URL=https://astrovox.ai
   NEXTAUTH_SECRET=<generate secure random string>
   ```

### Step 2: Deploy to Vercel
1. Go to https://vercel.com
2. Click "Add New..." ? "Project"
3. Import `AstrovoxAi` repo
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `apps/web`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
5. Add Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://astrovox-api.onrender.com
   NEXTAUTH_SECRET=<same as above>
   NEXTAUTH_URL=https://astrovox.ai
   ```
6. Click "Deploy"
7. Wait 2-3 minutes
8. Test: Open https://astrovox-ai.vercel.app

### Step 3: Custom Domain
1. In Vercel, go to Settings ? Domains
2. Add `astrovox.ai` and `www.astrovox.ai`
3. Update DNS records as instructed
4. Wait for SSL (automatic, 5-10 minutes)

## Landing Page Deployment (Vercel or Netlify)

### Option A: Same Vercel Project
- Landing page is already part of Next.js app at `/`

### Option B: Separate Static Host
1. Go to https://app.netlify.com
2. Drag and drop `landing/` folder
3. Configure custom domain: `astrovox.ai`

## Post-Deployment Verification

### Health Checks
- [ ] Backend: `curl https://astrovox-api.onrender.com/health` ? `{"status":"ok"}`
- [ ] Frontend: `curl https://astrovox.ai` ? 200 OK
- [ ] Database: `curl https://astrovox-api.onrender.com/healthz` ? `ok`

### Functional Tests
- [ ] User registration works
- [ ] Email verification sent
- [ ] Login works
- [ ] Chat endpoint returns response
- [ ] Streaming works
- [ ] Stripe checkout creates session
- [ ] Webhooks process correctly

### Performance Checks
- [ ] p99 latency < 500ms (cached)
- [ ] p99 latency < 5s (LLM)
- [ ] Uptime 100% (check with UptimeRobot)

## Monitoring Setup

### Sentry (Error Tracking)
1. Go to https://sentry.io
2. Create project: `astrovox-api`
3. Add DSN to Render env vars: `SENTRY_DSN`
4. Install: `pip install sentry-sdk`
5. Initialize in `app/main.py`

### UptimeRobot (Uptime Monitoring)
1. Go to https://uptimerobot.com
2. Add monitor:
   - Type: HTTPS
   - URL: `https://astrovox-api.onrender.com/health`
   - Interval: 5 minutes
3. Add alert contacts (email, Slack)

### Prometheus + Grafana (Optional)
1. Use Render's built-in metrics
2. Or deploy Grafana separately
3. Import dashboard from `monitoring/grafana-dashboard.json`

## Rollback Plan
If deployment fails:
1. Render: Click "Deployments" ? "Previous" ? "Promote"
2. Vercel: Click "Deployments" ? Previous ? "Promote"
3. Database: Render automatic backups (daily)

## Emergency Contacts
- Render Support: https://render.com/support
- Vercel Support: https://vercel.com/support
- Stripe Support: https://support.stripe.com
