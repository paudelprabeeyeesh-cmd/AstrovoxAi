# Installation Guide

This guide covers all supported installation methods for AstrovoxAI: local development, Docker, Docker Compose, Kubernetes, and production deployments.

## Prerequisites

| Tool | Minimum Version | Required | Notes |
|------|-----------------|----------|-------|
| Node.js | 18.x | Yes | Frontend runtime |
| Python | 3.9+ | Yes | Backend runtime |
| CUDA | 11.8+ | Recommended | GPU acceleration for training/inference |
| Docker | 24.x | Optional | Containerized deployment |
| Docker Compose | 2.x | Optional | Multi-service orchestration |
| Git | 2.x | Yes | Version control |
| Supabase CLI | Latest | Optional | Local database management |
| kubectl | 1.28+ | Optional | Kubernetes deployment |
| Helm | 3.12+ | Optional | Kubernetes package management |

### Platform-specific prerequisites

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y \
  python3.9 python3.9-venv python3-pip \
  nodejs npm git docker.io docker-compose

# macOS (Homebrew)
brew install python@3.9 node git docker docker-compose

# Windows (PowerShell, run as Administrator)
# Install from: https://www.python.org/downloads/windows/
# Install from: https://nodejs.org/en/download/
# Install Docker Desktop from: https://www.docker.com/products/docker-desktop
```

## Repository Setup

```bash
# Clone the repository
git clone https://github.com/astrovox/astrovox.git
cd astrovox

# Verify repository structure
ls -la
# Expected: 02-Backend/ frontend/ docs/ models/ docker-compose.yml ...
```

## Method 1: Docker Compose (Recommended)

The fastest way to get the full stack running.

### Step 1: Clone and configure

```bash
git clone https://github.com/astrovox/astrovox.git
cd astrovox
cp .env.example .env
```

### Step 2: Configure environment variables

Edit `.env` with your credentials:

```env
# Supabase (required)
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# AI Provider (at least one required)
OPENAI_API_KEY=sk-your-key-here
# ANTHROPIC_API_KEY=your_anthropic_key
# GEMINI_API_KEY=your_gemini_key
# GROQ_API_KEY=your_groq_key
# OLLAMA_BASE_URL=http://host.docker.internal:11434

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Step 3: Start all services

```bash
# Build and start all services in detached mode
docker-compose up --build -d

# View logs for all services
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f backend
```

### Step 4: Verify installation

```bash
# Backend health
curl http://localhost:8000/health
# Expected: {"status": "ok"}

# Frontend
# Open http://localhost:5173 in browser

# API documentation
# Open http://localhost:8000/docs in browser
```

### Step 5: Run database migrations

```bash
# Execute database/schemas/supabase_setup.sql in your Supabase SQL Editor
# Or via Supabase CLI:
supabase db push
```

## Method 2: Manual Development Setup

### Step 1: Clone repository

```bash
git clone https://github.com/astrovox/astrovox.git
cd astrovox
cp .env.example .env
```

### Step 2: Backend setup

```bash
cd 02-Backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# Verify installation
python -c "import fastapi; import torch; print('Backend dependencies OK')"
```

### Step 3: Frontend setup

```bash
cd <project-root>

# Install dependencies
npm install

# Verify installation
npm run typecheck
```

### Step 4: Start development servers

```bash
# Terminal 1: Backend
cd 02-Backend
source venv/bin/activate  # or venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
npm run dev
```

### Step 5: Configure database

```bash
# Option A: Automated setup
bash scripts/setup-database.sh
# Windows PowerShell:
powershell -ExecutionPolicy Bypass -File scripts/setup-database.ps1

# Option B: Manual setup
# 1. Go to https://app.supabase.com
# 2. Open your project → SQL Editor
# 3. Paste contents of database/schemas/supabase_setup.sql
# 4. Execute migrations in database/migrations/
```

## Method 3: Production Docker Deployment

```bash
# Use production Compose file
cp .env.example .env
# Edit .env with production values

# Start with production profile
docker-compose -f docker-compose.prod.yml up --build -d

# Verify
curl https://yourdomain.com/health
curl https://yourdomain.com/metrics
```

### Production environment variables

```env
ENVIRONMENT=production
DEBUG=false
ALLOWED_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
FRONTEND_URL=https://app.yourdomain.com
LOG_LEVEL=WARNING
SECRET_KEY=<generate-with-openssl-rand-base64-32>
JWT_SECRET_KEY=<generate-with-openssl-rand-base64-32>
```

## Method 4: Kubernetes Deployment

### Prerequisites

```bash
# Create namespace
kubectl create namespace astrovox

# Add secrets
kubectl create secret generic astrovox-secrets \
  --from-literal=supabase-url=https://your-project.supabase.co \
  --from-literal=supabase-service-role-key=your_key \
  --from-literal=openai-api-key=sk-your-key \
  -n astrovox
```

### Deploy with Helm

```bash
# Add/update chart
helm upgrade --install astrovox ./helm \
  --namespace astrovox \
  --values helm/values.yaml \
  --set backend.image.tag=latest \
  --set frontend.image.tag=latest
```

### Deploy with kubectl

```bash
# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/ingress.yaml

# Verify deployment
kubectl get pods -n astrovox
kubectl get ingress -n astrovox
```

## Method 5: Model Training Environment

```bash
# Install ML dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install project ML dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Install optional training extras
pip install bitsandbytes trl peft accelerate deepspeed wandb

# Verify GPU
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0)}')"
```

## Verification Checklist

```bash
# 1. Backend health
curl http://localhost:8000/health
# Expected: {"status": "ok"}

# 2. Backend readiness
curl http://localhost:8000/health/ready
# Expected: {"status": "ready", "checks": {"database": "healthy", ...}}

# 3. API documentation accessible
curl -s http://localhost:8000/docs | head -5

# 4. Frontend accessible
curl -s http://localhost:5173 | head -5

# 5. Authentication works
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test123!","username":"testuser"}'

# 6. Metrics endpoint
curl http://localhost:8000/metrics | head -10

# 7. Model training test
python examples/train_tiny.py --config models/llm/configs/config_100m.yaml --epochs 1

# 8. Model inference test
python examples/generate.py --prompt "Hello" --checkpoint model.pt --max-tokens 10
```

## Common Installation Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `npm install` fails | Node version < 18 | Upgrade Node.js |
| `pip install` fails on Windows | Missing C++ Build Tools | Install Visual Studio Build Tools |
| Port 8000 in use | Another service running | Change `SERVER_PORT` in `.env` |
| Port 5173 in use | Another dev server | Change Vite port in `vite.config.js` |
| CUDA out of memory | Model too large for GPU | Enable gradient checkpointing in config |
| Database connection refused | Supabase project paused | Resume project in Supabase dashboard |
| CORS errors | Frontend URL not in `ALLOWED_ORIGINS` | Add origin to `.env` |

## Environment Variables Reference

See `.env.example` for the complete list. Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_SUPABASE_URL` | Yes | — | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | — | Supabase anonymous key |
| `VITE_API_URL` | No | `http://localhost:8000` | Backend API URL |
| `SUPABASE_URL` | Yes | — | Supabase URL (backend) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key |
| `OPENAI_API_KEY` | Yes* | — | OpenAI API key |
| `ALLOWED_ORIGINS` | No | `*` | CORS origins |
| `RATE_LIMIT` | No | `120/minute` | Rate limit config |
| `DAILY_AI_LIMIT` | No | `50` | Daily AI quota |
| `ENVIRONMENT` | No | `development` | Environment mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |

*At least one AI provider key is required.

## Uninstallation

```bash
# Docker Compose
docker-compose down -v  # Removes containers and volumes

# Manual
# 1. Deactivate virtual environment
deactivate
# 2. Remove node_modules
rm -rf node_modules
# 3. Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
# 4. Remove logs and checkpoints
rm -rf phase1_logs phase1_checkpoints
```
