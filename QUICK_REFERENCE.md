# Astravox AI - Quick Reference Guide

## 🚀 Essential Commands

### Start Server
```bash
python main.py
# or
python 02-Backend/server/app.py
```

### Run Tests
```bash
pytest 02-Backend/tests/ -v          # All tests
pytest 02-Backend/tests/test_utils.py -v  # Unit tests only
pytest 02-Backend/tests/ --cov       # With coverage
```

### Watch Logs
```bash
tail -f logs/astravox.log
```

### Install Dependencies
```bash
pip install -r requirements.txt
pip install pytest pytest-cov  # Testing
```

## 🗂️ Important Files

### Configuration
| File | Purpose |
|------|---------|
| `.env` | Local environment (DO NOT COMMIT) |
| `.env.example` | Template for developers |
| `requirements.txt` | Python dependencies |

### Backend Entry Points
| File | Purpose |
|------|---------|
| `02-Backend/server/app.py` | Flask app factory |
| `main.py` | Entry point |

### Routes
| File | Endpoints |
|------|-----------|
| `02-Backend/routes/chat_routes.py` | `/chat/*` |
| `02-Backend/routes/auth_routes.py` | `/auth/*` |
| `02-Backend/routes/api_routes.py` | `/api/*` |
| `02-Backend/routes/page_routes.py` | `/` (frontend) |

### Utilities
| File | Purpose |
|------|---------|
| `02-Backend/utils/logger.py` | Logging setup |
| `02-Backend/utils/middleware.py` | Request tracking |
| `02-Backend/utils/validators.py` | Input validation |

### AI Integration
| File | Purpose |
|------|---------|
| `AI-Integration/ai_logic/ai_router.py` | AI orchestration |
| `AI-Integration/ai_logic/memory.py` | Memory management |
| `AI-Integration/ai_logic/memory_sql.py` | SQLite backend |
| `AI-Integration/ai_logic/gemini.py` | Gemini API client |

### Frontend
| File | Purpose |
|------|---------|
| `Frontend/index.html` | Chat UI |

### Tests
| File | Purpose |
|------|---------|
| `02-Backend/tests/conftest.py` | Test fixtures |
| `02-Backend/tests/test_utils.py` | Unit tests |
| `02-Backend/tests/test_routes.py` | Integration tests |

### Documentation
| File | Purpose |
|------|---------|
| `DEVELOPMENT_GUIDE.md` | Complete development guide |
| `SESSION_SUMMARY.md` | What was done in this session |
| This file | Quick reference |

## 📍 Key Locations

### Logs
```
logs/
└── astravox.log        # All application logs
```

### Database
```
02-Backend/
├── database/
│   └── chat.db         # SQLite chat database
└── database/
    └── memory.db       # SQLite memory database
```

### Memory Files
```
AI-Integration/ai_logic/
├── chat_history_db.json  # Legacy JSON memory (fallback)
└── memory.db             # SQLite memory (recommended)
```

## 🔗 API Quick Reference

### Chat API
```bash
# Send message (get full response)
POST /chat/message
{
  "message": "Hello",
  "conversation_id": "conv-123"
}

# Stream response
POST /chat/stream
{
  "message": "Hello",
  "conversation_id": "conv-123"
}

# Get history
GET /chat/history/conv-123

# Health check
GET /chat/health
```

### Auth API
```bash
# Register
POST /auth/register
{
  "username": "user",
  "email": "user@example.com",
  "password": "password"
}

# Login
POST /auth/login
{
  "username": "user",
  "password": "password"
}

# Check status
GET /auth/status
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Required
GEMINI_API_KEY=your-key

# Optional
SECRET_KEY=your-secret           # Session encryption
DEBUG_MODE=False                 # Debug logging
DEMO_MODE=0                      # Demo user access
MEMORY_BACKEND=sqlite            # sqlite or json
RATE_LIMIT_PER_DAY=200          # Max requests/day
RATE_LIMIT_PER_HOUR=50          # Max requests/hour
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
```

## 📊 Logging

### Log Levels
```python
logger.debug()      # Development details
logger.info()       # Important events
logger.warning()    # Warning messages
logger.error()      # Errors (exc_info=True)
```

### Use Specific Loggers
```python
from utils.logger import chat_logger, ai_logger, auth_logger

chat_logger.info("Chat event")
ai_logger.info("AI event")
auth_logger.info("Auth event")
```

### Log Rotation
- File: `logs/astravox.log`
- Max size: 10MB
- Backups: 5 files
- Auto-rotates when full

## ✅ Validation Examples

```python
from utils.validators import validate_email, sanitize_string

# Email validation
if not validate_email(email):
    return error("Invalid email")

# String sanitization
clean_text = sanitize_string(user_input, max_length=1000)

# Using decorators
@require_json
@require_fields("field1", "field2")
def my_route():
    pass
```

## 🧪 Testing Tips

### Run Single Test
```bash
pytest 02-Backend/tests/test_utils.py::TestValidators::test_email -v
```

### Generate Coverage Report
```bash
pytest 02-Backend/tests/ --cov=02-Backend --cov-report=html
# Open htmlcov/index.html in browser
```

### Debug Test
```bash
pytest 02-Backend/tests/ -v -s --pdb  # Drop into debugger on failure
```

## 🐛 Common Issues

### API Key Not Found
```bash
# Add to .env
GEMINI_API_KEY=your-key

# Or export
export GEMINI_API_KEY=your-key
```

### Database Locked
```bash
# Close other connections
# Kill running processes
pkill -f "python main.py"
```

### Port Already in Use
```bash
# Check what's using port 5000
lsof -i :5000
# Kill the process
kill -9 <PID>
```

### Tests Failing
```bash
# Clear cache
rm -rf .pytest_cache
rm -rf __pycache__

# Re-run tests
pytest 02-Backend/tests/ -v --tb=short
```

## 📱 Architecture Quick View

```
User Browser
    ↓
Frontend (HTML/CSS/JS)
    ↓
Flask Routes
    ↓
Middleware (Logging, Validation)
    ↓
Business Logic
    ↓ branches to ↓         ↓         ↓
Database  |  Memory System  |  AI Engine
(chat.db) |  (memory.db)    |  (Gemini)
```

## 💡 Best Practices

1. **Always validate input**
   ```python
   text = sanitize_string(user_input)
   ```

2. **Always log important events**
   ```python
   logger.info(f"User {user_id} did X")
   ```

3. **Always handle errors**
   ```python
   try:
       result = operation()
   except Exception as e:
       logger.error(f"Error: {e}", exc_info=True)
   ```

4. **Never commit secrets**
   ```bash
   # Good: Use .env
   # Bad: Hardcode GEMINI_API_KEY
   ```

5. **Always test changes**
   ```bash
   pytest 02-Backend/tests/ -v
   ```

## 🔗 External Resources

- [Flask Docs](https://flask.palletsprojects.com/)
- [Gemini API](https://ai.google.dev/)
- [Pytest](https://docs.pytest.org/)
- [SQLite](https://www.sqlite.org/)

## 📞 Support

1. Check `DEVELOPMENT_GUIDE.md`
2. Check `SESSION_SUMMARY.md`
3. Review logs: `tail -f logs/astravox.log`
4. Run tests: `pytest 02-Backend/tests/ -v`

---

**Last Updated**: 2026-06-07  
**Version**: 1.0.0  
**Status**: ✅ Production Ready
