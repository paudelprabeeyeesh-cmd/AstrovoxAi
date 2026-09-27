# Troubleshooting Guide

This guide covers common issues and solutions for AstrovoxAI installation, development, training, inference, and production deployment.

## Installation Issues

### Docker Compose fails to start

```bash
# Check Docker is running
docker info

# Check available resources
docker system info | grep -E "Total Memory|CPUs"

# View service logs
docker-compose logs backend
docker-compose logs frontend

# Common fixes
docker-compose down -v
docker-compose up --build --force-recreate
```

### Python dependency installation fails

```bash
# Windows: Install C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel

# Install with no binary (force source build)
pip install --no-binary :all: torch --index-url https://download.pytorch.org/whl/cu121

# Use pre-built wheels
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### Node.js version mismatch

```bash
# Check version
node --version  # Should be 18+

# Use nvm to manage versions
nvm install 18
nvm use 18

# Clear npm cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

## Backend Issues

### Backend won't start

```bash
# Check port availability
netstat -ano | findstr :8000
lsof -i :8000

# Check environment variables
cd 02-Backend
python -c "from app.config import settings; print(settings)"

# Start with verbose logging
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload --log-level debug
```

### Database connection errors

```bash
# Test connection directly
psql $SUPABASE_URL -c "SELECT 1"

# Check Supabase status
curl https://api.supabase.com/v1/projects/$PROJECT_ID/status

# Verify credentials in .env
grep SUPABASE .env

# Check IP allowlisting in Supabase dashboard
# Settings → Database → Connection pooling → IP allowlist
```

### AI Provider errors

```bash
# Test OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Anthropic
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-sonnet","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'

# Test Ollama
curl http://localhost:11434/api/tags
```

### Rate limiting issues

```python
# Check rate limit headers in response
response = requests.get(url, headers=headers)
print(response.headers.get("X-RateLimit-Remaining"))
print(response.headers.get("X-RateLimit-Reset"))

# Implement exponential backoff
import time
import random

def call_with_backoff(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
    raise MaxRetriesExceeded()
```

## Frontend Issues

### Frontend won't start

```bash
# Clear caches
rm -rf .vite node_modules/.vite
npm run dev -- --force

# Check TypeScript errors
npm run typecheck

# Check for port conflicts
lsof -i :5173

# Use different port
npm run dev -- --port 3000
```

### CORS errors

```bash
# Verify CORS configuration
grep ALLOWED_ORIGINS .env

# Backend should include frontend origin
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Check browser console for blocked origin
# Add the blocked origin to ALLOWED_ORIGINS
```

### API calls failing

```javascript
// Check VITE_API_URL in frontend .env
// Should point to backend URL
VITE_API_URL=http://localhost:8000

// Debug API calls in browser DevTools
// Network tab → check request/response

// Verify auth token
const token = localStorage.getItem("token");
console.log("Token:", token ? `${token.slice(0, 20)}...` : "MISSING");
```

## Training Issues

### CUDA out of memory

```python
# Reduce batch size
config["batch_size"] = 1
config["gradient_accumulation_steps"] = 32

# Enable gradient checkpointing
config["gradient_checkpointing"] = True

# Use mixed precision
config["mixed_precision"] = "bf16"  # or "fp16"

# Clear CUDA cache
import torch
torch.cuda.empty_cache()

# Use CPU offloading (for FSDP)
config["cpu_offload"] = True
```

### NaN/Inf loss

```python
# Check learning rate (reduce if needed)
config["lr"] = 1e-5  # Reduce from 3e-4

# Enable gradient clipping
config["gradient_clip_norm"] = 1.0

# Check for data issues
# - NaN values in dataset
# - Extremely long sequences
# - Empty samples

# Add loss stabilization
def safe_loss(loss):
    if torch.isnan(loss) or torch.isinf(loss):
        return torch.tensor(0.0, device=loss.device, requires_grad=True)
    return loss
```

### Slow training

```bash
# Check GPU utilization
nvidia-smi -l 1

# Verify data loading isn't bottleneck
# Increase num_workers in DataLoader
num_workers=4

# Use pinned memory for CUDA
pin_memory=True

# Use mixed precision
mixed_precision=bf16

# Enable flash attention
pip install flash-attn
```

## Inference Issues

### Slow inference

```python
# Enable KV cache
engine.enable_kv_cache()

# Use quantization
quantizer = Quantizer(model, method="awq", bits=4)
model = quantizer.quantize()

# Use tensor parallelism
engine = InferenceEngine(model, tensor_parallel_size=4)

# Reduce max_new_tokens
max_new_tokens = 100  # instead of 1000
```

### Memory leaks during inference

```python
# Clear CUDA cache between requests
torch.cuda.empty_cache()

# Use torch.no_grad() for inference
with torch.no_grad():
    output = model(input_ids)

# Delete tensors explicitly
del output
del input_ids
gc.collect()
torch.cuda.empty_cache()
```

### Hallucination issues

```python
from models.llm.inference.optimization import HallucinationDetector

detector = HallucinationDetector()

result = detector.check(
    generated_text=response,
    source_documents=context_docs,
    threshold=0.7
)

if result.has_hallucinations:
    print(f"Detected hallucinations: {result.spans}")
    # Regenerate with stricter constraints
    response = engine.generate(
        prompt=prompt,
        temperature=0.3,  # Lower temperature
        top_p=0.8,
        repetition_penalty=1.3,
        max_new_tokens=100
    )
```

## Docker Issues

### Container exits immediately

```bash
# Check logs
docker logs <container-name>

# Run interactively
docker run -it astrovox/backend:latest /bin/bash

# Check environment variables
docker exec <container> env | grep SUPABASE
```

### Volume permission issues

```bash
# Fix ownership (Linux)
sudo chown -R 1000:1000 ./storage ./checkpoints ./logs

# Windows: Ensure paths are mounted correctly
# Use named volumes instead of bind mounts on Windows
```

### GPU not available in container

```bash
# Verify NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi

# In docker-compose.yml
services:
  backend:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

## Database Issues

### Migration failures

```sql
-- Check migration status
SELECT * FROM supabase_migrations.schema_migrations;

-- Rollback migration
-- Manually reverse SQL in reverse order

-- Re-run migrations
-- Execute files in database/migrations/ in order
```

### RLS policy issues

```sql
-- Check RLS policies
SELECT * FROM pg_policies WHERE tablename = 'conversations';

-- Temporarily disable RLS for debugging
ALTER TABLE conversations DISABLE ROW LEVEL SECURITY;

-- Re-enable after debugging
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
```

### Slow queries

```sql
-- Analyze query plan
EXPLAIN ANALYZE SELECT * FROM messages WHERE conversation_id = 1;

-- Check indexes
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'messages';

-- Add missing index
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
```

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `CUDA out of memory` | Batch too large | Reduce batch size, enable gradient checkpointing |
| `Connection refused` | Service not running | Start service, check port |
| `401 Unauthorized` | Invalid/missing token | Refresh token, check JWT config |
| `429 Too Many Requests` | Rate limit hit | Wait, implement backoff, increase limit |
| `500 Internal Server Error` | Server bug | Check logs, report issue |
| `404 Not Found` | Wrong URL or resource missing | Check endpoint path |
| `422 Validation Error` | Invalid request body | Check request schema |
| `ImportError` | Missing dependency | Install requirements.txt |
| `FileNotFoundError` | Missing file | Check paths, create file |
| `KeyError` | Missing config key | Check config file |

## Logs and Debugging

```bash
# Backend logs (Docker)
docker-compose logs -f backend

# Backend logs (direct)
cd 02-Backend
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --reload

# Frontend logs
npm run dev 2>&1 | tee frontend.log

# Training logs
tensorboard --logdir phase1_logs/

# Model logs
tail -f phase1_logs/training_metrics.csv
```

## Getting Help

1. Search [GitHub Issues](https://github.com/astrovox/astrovox/issues)
2. Check [Discussions](https://github.com/astrovox/astrovox/discussions)
3. Review [Support Documentation](./SUPPORT.md)
4. Contact support: support@astrovox.ai
