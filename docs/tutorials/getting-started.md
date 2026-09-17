# Tutorial: Getting Started with AstrovoxAI

## Prerequisites
- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- Git

## Step 1: Clone Repository
```bash
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi
```

## Step 2: Start Backend
```bash
cd 02-Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Step 3: Start Frontend
```bash
cd apps/web
npm install
npm run dev
```

## Step 4: Access Application
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Step 5: Make Your First Request
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"secure123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"secure123"}'

# Solve
curl -X POST http://localhost:8000/solve \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, world!"}'
```

## Next Steps
- Read [Architecture Overview](./architecture.md)
- Explore [API Reference](../02-Backend/docs/sdk_reference.md)
- Try [RAG Tutorial](./rag-tutorial.md)
