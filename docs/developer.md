# Developer Guide

This guide covers AstrovoxAI development workflows, code organization, testing, debugging, and contribution guidelines.

## Project Structure

```
AstrovoxAi/
├── src/                        # React frontend (Vite + TypeScript)
│   ├── components/             # UI components
│   ├── hooks/                  # Custom React hooks
│   ├── services/               # Frontend services (API clients)
│   ├── utils/                  # Utilities
│   ├── platform/               # PWA, offline sync
│   ├── mobile/                 # Mobile adapters
│   ├── terminal/               # Terminal engine
│   ├── design/                 # Design system
│   ├── app.jsx                 # Main app component
│   ├── auth.jsx                # Authentication UI
│   ├── Chat.jsx                # Chat interface
│   ├── Sidebar.jsx             # Conversation sidebar
│   ├── MemoryPanel.jsx         # Memory management
│   ├── SettingsPanel.jsx       # User settings
│   └── terminalconsole.jsx     # Terminal console
├── 02-Backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── api/                # API routers
│   │   ├── providers/          # AI provider implementations
│   │   ├── aios/               # AI Operating System
│   │   ├── agi_reasoning/      # AGI reasoning modules
│   │   ├── enterprise/         # Enterprise features
│   │   ├── billing/            # Billing & subscriptions
│   │   ├── analytics/          # Analytics engine
│   │   ├── middleware/         # Security & request middleware
│   │   ├── chat.py             # Chat routes
│   │   ├── memory.py           # Memory routes
│   │   ├── terminal.py         # Terminal routes
│   │   ├── embeddings_route.py # Embeddings API
│   │   ├── database.py         # Database operations
│   │   ├── metrics.py          # Prometheus metrics
│   │   └── providers/          # LLM provider adapters
│   └── tests/                  # Backend tests
├── models/                     # LLM model code
│   └── llm/
│       ├── model/              # Transformer architecture
│       ├── trainer/            # Pre-training and fine-tuning
│       ├── tokenizer/          # Tokenizer training
│       ├── inference/          # Generation engine + server
│       ├── evaluation/         # Benchmark harness
│       ├── training_data/      # Dataset pipeline
│       ├── configs/            # Model size configs
│       └── quantization.py     # INT8/FP16/BF16 quantization
├── examples/                   # Developer examples
├── tests/                      # Model tests
├── scripts/                    # Benchmark scripts
├── docs/                       # Documentation
├── database/                   # Database schemas
├── frontend/                   # Legacy frontend assets
├── sdk/                        # Generated SDKs
├── charts/                     # Helm charts
├── k8s/                        # Kubernetes manifests
├── monitoring/                 # Prometheus/Grafana configs
└── docker-compose.yml          # Docker Compose
```

## Backend Development

### Running the API

```bash
cd 02-Backend

# Development with auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production-like (no reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# With specific log level
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload --log-level debug
```

### Running Tests

```bash
cd 02-Backend

# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_executor_compiler.py

# Specific test
pytest tests/test_executor_compiler.py::CompilerTest::test_fusion -v

# Parallel execution
pytest -n auto
```

### Adding a New API Endpoint

1. **Create the route file** (if new domain):

```python
# app/api/routers/my_feature.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

class MyRequest(BaseModel):
    field: str

class MyResponse(BaseModel):
    result: str

@router.post("/process", response_model=MyResponse)
async def process(request: MyRequest, user=Depends(get_current_user)):
    return MyResponse(result=f"Processed: {request.field}")
```

2. **Register in `app/main.py`**:

```python
from app.api.routers.my_feature import router as my_feature_router
app.include_router(my_feature_router)
```

3. **Add tests**:

```python
# tests/test_my_feature.py
def test_process(client, auth_headers):
    response = client.post(
        "/api/v1/my-feature/process",
        json={"field": "test"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["result"] == "Processed: test"
```

### Adding a New AI Provider

1. **Create provider class**:

```python
# app/providers/my_provider.py
from app.providers.base import BaseProvider

class MyProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = MyClient(api_key)

    async def chat(self, messages, model, **kwargs) -> str:
        response = await self.client.chat(messages=messages, model=model, **kwargs)
        return response.content

    async def stream(self, messages, model, **kwargs):
        async for chunk in self.client.stream(messages=messages, model=model, **kwargs):
            yield chunk.text

    def count_tokens(self, text: str) -> int:
        return len(text.split())  # Approximate
```

2. **Register in factory**:

```python
# app/providers/factory.py
from app.providers.my_provider import MyProvider

class ProviderFactory:
    _providers = {
        "my-model": MyProvider,
        # ... existing providers
    }
```

3. **Add tests**:

```python
# tests/providers/test_my_provider.py
def test_chat(mock_my_client):
    provider = MyProvider(api_key="test-key")
    response = asyncio.run(provider.chat([{"role": "user", "content": "hi"}]))
    assert response is not None
```

### Adding Middleware

```python
# app/middleware/my_middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class MyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Pre-processing
        start = time.time()

        response = await call_next(request)

        # Post-processing
        elapsed = time.time() - start
        response.headers["X-Process-Time"] = str(elapsed)
        return response
```

Register in `app/main.py`:

```python
from app.middleware.my_middleware import MyMiddleware
app.add_middleware(MyMiddleware)
```

## Frontend Development

### Running the Dev Server

```bash
# Default (port 5173)
npm run dev

# Custom port
npm run dev -- --port 3000

# With HTTPS
npm run dev -- --https
```

### Adding a New Page

```jsx
// src/MyPage.jsx
import { useState, useEffect } from 'react';

export default function MyPage() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/api/v1/my-endpoint')
      .then(res => res.json())
      .then(setData);
  }, []);

  return <div>{JSON.stringify(data)}</div>;
}
```

Register route:

```jsx
// src/app.jsx
import MyPage from './MyPage';
<Route path="/my-page" element={<MyPage />} />
```

### Using the API Service

```javascript
// src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

// Add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const chatApi = {
  sendMessage: (data) => api.post('/chat/message', data),
  getConversations: () => api.get('/chat/conversations'),
};

export default api;
```

## Model Development

### Running Training

```bash
# Phase 1 training (synthetic data, quick test)
python phase1_train.py --config models/llm/configs/config_100m.yaml

# Full training
python -m models.llm.trainer.train --config models/llm/configs/config_1b.yaml

# Resume from checkpoint
python phase1_train.py --config config_1b.yaml --resume checkpoints/latest.pt

# Multi-GPU training
torchrun --nproc_per_node=4 -m models.llm.trainer.train --config config_7b.yaml
```

### Running Inference

```bash
# Generate text
python -m models.llm.inference.generate --checkpoint model.pt --prompt "Hello world" --max-tokens 100

# Start API server
python -m models.llm.inference.chat --config models/llm/configs/config_7b.yaml --checkpoint model.pt --port 8000

# Evaluate model
python phase1_evaluate.py --checkpoint-dir phase1_checkpoints --output-dir model.pt
```

### Exporting Models

```bash
# Export to HuggingFace format
python -m models.llm.export --checkpoint model.pt --config config_7b.yaml --format huggingface --output-dir export/hf

# Export to ONNX
python -m models.llm.export --checkpoint model.pt --config config_7b.yaml --format onnx --output-dir export/onnx

# Export to GGUF
python -m models.llm.export --checkpoint model.pt --config config_7b.yaml --format gguf --output-dir export/gguf
```

## Debugging

### Backend Logging

```python
from app.logging_config import get_logger

logger = get_logger(__name__)

logger.debug("Detailed debug info: %s", details)
logger.info("User %s performed action", user_id)
logger.warning("Rate limit approaching for %s", user_id)
logger.error("Failed to process request: %s", exc_info=True)
```

### Frontend Debugging

```javascript
// Enable React DevTools
// Install React DevTools browser extension

// Debug API calls
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL });
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);
```

### Model Debugging

```python
# Profile memory usage
from models.llm.memory_optimization import profile_memory

with profile_memory():
    output = model(input_ids, labels=labels)

# Check gradients
for name, param in model.named_parameters():
    if param.grad is not None:
        print(f"{name}: grad_norm={param.grad.norm().item():.4f}")

# Visualize attention (if applicable)
from models.llm.model.visualization import visualize_attention
visualize_attention(model, input_ids, layer=0, head=0)
```

## Code Standards

### Python

- Follow PEP 8 with Black formatter
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Docstrings for all public functions/classes
- Import sorting with `isort`

```bash
# Format
black 02-Backend/ models/
isort 02-Backend/ models/

# Lint
ruff check 02-Backend/ models/

# Type check
mypy 02-Backend/app --strict
```

### TypeScript

- Use strict mode
- Prefer functional components with hooks
- Use `interface` over `type` for object shapes
- Maximum line length: 100 characters

```bash
# Lint
npm run lint

# Type check
npm run typecheck
```

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-new-feature

# Make changes and commit
git add .
git commit -m "feat: add my new feature"

# Push and create PR
git push origin feature/my-new-feature
# Create PR via GitHub
```

Commit message format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

## Testing

### Backend Tests

```bash
cd 02-Backend

# Run all
pytest

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=app --cov-report=term-missing
```

### Model Tests

```bash
# Unit tests
pytest tests/test_model.py -v

# Integration tests
pytest tests/test_inference.py -v

# Benchmark tests
pytest tests/test_benchmarks.py -v
```

### Frontend Tests

```bash
# Unit tests
npm run test

# E2E tests
npm run test:e2e

# Coverage
npm run test:coverage
```

## Environment Setup Scripts

```bash
#!/bin/bash
# setup-dev.sh
set -e

echo "Setting up AstrovoxAI development environment..."

# Backend
cd 02-Backend
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
cd ..

# Frontend
npm install

# Database
echo "Run database/schemas/supabase_setup.sql in Supabase SQL Editor"

echo "Setup complete! Run:"
echo "  Backend: cd 02-Backend && python -m uvicorn app.main:app --reload"
echo "  Frontend: npm run dev"
```

```powershell
# setup-dev.ps1
Write-Host "Setting up AstrovoxAI development environment..."

# Backend
Set-Location 02-Backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
Set-Location ..

# Frontend
npm install

Write-Host "Setup complete!"
```

## Common Development Tasks

### Add a new AI model to the registry

1. Update `app/providers/models.py`
2. Add provider class in `app/providers/`
3. Register in factory
4. Add tests
5. Update API docs

### Add a new database table

1. Create migration in `database/migrations/`
2. Update ORM models in `app/database.py`
3. Add RLS policies
4. Create repository in `app/repositories/`
5. Add tests

### Add a new benchmark

1. Create benchmark class in `models/llm/evaluation/benchmarks.py`
2. Add test data
3. Register in `BenchmarkSuite`
4. Update docs

## Performance Tips

1. **Backend**: Use async I/O, enable caching, optimize queries
2. **Frontend**: Lazy load components, memoize expensive computations
3. **Models**: Use mixed precision, gradient checkpointing, flash attention
4. **Database**: Add indexes, use connection pooling, enable RLS efficiently

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | Ensure venv is active, run from correct directory |
| Port conflicts | Change ports in `.env` or config files |
| Test failures | Run in isolation: `pytest tests/test_file.py::test_name` |
| Slow builds | Clear caches: `npm run clean`, `rm -rf __pycache__` |
| CUDA issues | Check `nvidia-smi`, verify CUDA toolkit installation |
