# AstrovoxAI — Next 48 Hours (CRITICAL)

## Hour 1-2: Deploy to Production
1. Go to https://render.com and sign up/login
2. Click "New +" ? "Web Service"
3. Connect GitHub repo: paudelprabeeyeesh-cmd/AstrovoxAi
4. Configure:
   - Name: astrovox-api
   - Environment: Docker
   - Branch: main
   - Plan: Standard (/mo)
5. Add PostgreSQL:
   - Click "New +" ? "PostgreSQL"
   - Name: astrovox-db
   - Plan: Free
   - Copy the DATABASE_URL
6. Add Redis:
   - Click "New +" ? "Redis"
   - Name: astrovox-redis
   - Copy the REDIS_URL
7. Set environment variables in astrovox-api:
   - DATABASE_URL = <from PostgreSQL>
   - REDIS_URL = <from Redis>
   - OPENAI_API_KEY = <your key>
   - STRIPE_SECRET_KEY = <your key>
   - STRIPE_WEBHOOK_SECRET = <your secret>
   - JWT_SECRET_KEY = <generate secure random string>
   - ALLOWED_ORIGINS = https://astrovox.ai,https://www.astrovox.ai
8. Click "Create Web Service"
9. Wait for deployment (5-10 minutes)
10. Test: curl https://astrovox-api.onrender.com/health

## Hour 3-4: Domain Setup
1. Buy domain astrovox.ai (or use existing)
2. In Render, go to astrovox-api ? Settings ? Custom Domains
3. Add astrovox.ai and www.astrovox.ai
4. Update DNS records as instructed by Render
5. Wait for SSL certificate (automatic, 5-10 minutes)

## Hour 5-6: Landing Page Deployment
1. Go to Render ? New + ? "Static Site"
2. Connect GitHub repo
3. Name: astrovox-landing
4. Build Command: (none - static site)
5. Publish Directory: ./landing
6. Add custom domain: astrovox.ai (root)
7. Deploy

## Hour 7-8: Stripe Configuration
1. Go to https://dashboard.stripe.com
2. Get API keys (test mode first)
3. Set webhook endpoint: https://astrovox-api.onrender.com/webhooks/stripe
4. Select events: checkout.session.completed, customer.subscription.created, invoice.payment_succeeded, invoice.payment_failed
5. Copy webhook secret to Render env vars

## Hour 9-12: Testing
1. Test signup flow: POST /auth/register
2. Test login: POST /auth/login
3. Test solve: POST /solve with auth token
4. Test streaming: POST /solve/stream
5. Test Stripe checkout: POST /billing/checkout
6. Test webhook: Use Stripe CLI to test webhooks locally

## Hour 13-24: First Customers
1. Send 100 personalized emails to prospects:
   - Subject: "AI infrastructure for your sales team"
   - Body: "We just launched AstrovoxAI. Would you like to try it for free?"
2. Post on Product Hunt, Hacker News, Twitter
3. Schedule 10 demo calls
4. Close first 3 paying customers

## Day 2: Iterate
1. Review feedback from first users
2. Fix critical bugs
3. Improve onboarding flow
4. Release v0.1.1
