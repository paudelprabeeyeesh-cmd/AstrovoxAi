# Astravox AI Platform - Development Guide

**Last Updated**: 2026-06-07  
**Platform Status**: Production-Ready (Phase 1 Complete)

## 📋 Overview

This is a comprehensive guide for the improved Astravox AI platform. This document covers:
- New features and improvements
- Architecture and structure
- How to run and test the system
- Development best practices

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example)
cp .env.example .env

# Add your GEMINI_API_KEY to .env
# Never commit .env to git!
```

### 2. Run the Server

```bash
# Start the Flask server
python main.py

# Server runs at http://127.0.0.1:5000
# Chat UI available at http://127.0.0.1:5000
```

### 3. Test the API

```bash
# Chat endpoint
curl -X POST http://127.0.0.1:5000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello!",
    "conversation_id": "test-1"
  }'
```

## 📁 Project Structure

### Backend Organization

```
02-Backend/
├── server/
│   └── app.py              # Flask app factory with logging
├── routes/
│   ├── chat_routes.py      # Chat endpoints (streaming, message)
│   ├── auth_routes.py      # Authentication (register, login)
│   ├── api_routes.py       # API endpoints
│   └── page_routes.py      # Page serving
├── database/
│   ├── database.py         # SQLite connection & queries
│   └── chat.db             # Chat database
├── utils/
│   ├── logger.py           # Logging setup
│   ├── middleware.py       # Request tracking
│   ├── validators.py       # Input validation
│   └── __init__.py
└── tests/
    ├── conftest.py         # Test fixtures
    ├── test_utils.py       # Unit tests
    ├── test_routes.py      # Integration tests
    └── run_tests.py        # Test runner
```

### Frontend

```
Frontend/
├── index.html              # Redesigned chat UI
├── css/                    # Stylesheets
├── js/                     # JavaScript modules
└── components/             # Reusable components
```

### AI Integration

```
AI-Integration/
├── ai_logic/
│   ├── ai_router.py        # Orchestrator
│   ├── memory.py           # Flexible memory backend
│   ├── memory_sql.py       # SQLite memory system
│   ├── gemini.py           # Gemini API client
│   ├── response_handler.py # Response formatting
│   ├── context_manager.py  # History management
│   └── formatter.py        # Text sanitization
└── prompts/                # System prompts
```

## 🔐 Security

### Environment Variables

Never commit `.env` to git. Use `.env.example` as template:

```bash
# .env (DO NOT COMMIT)
GEMINI_API_KEY=your-actual-key
SECRET_KEY=your-secret-key-min-32-chars
```

### API Key Safety

- Never hardcode API keys in code
- Use environment variables only
- Rotate keys regularly
- Use rate limiting (configured in app.py)

### Input Validation

All user input is validated and sanitized:

```python
from utils.validators import sanitize_string, validate_email

# Automatic sanitization
clean_text = sanitize_string(user_input, max_length=5000)

# Validation with decorators
@require_json
@require_fields("message", "conversation_id")
def my_route():
    pass
```

## 📊 Logging

### Log Files

- Location: `./logs/astravox.log`
- Auto-rotating: 10MB max, keeps 5 backups
- Format: `[TIMESTAMP] [LOGGER] [LEVEL] MESSAGE`

### Log Levels

```python
from utils.logger import chat_logger

chat_logger.debug("Development details")
chat_logger.info("User action: message sent")
chat_logger.warning("Rate limit approaching")
chat_logger.error("Failed to save message", exc_info=True)
```

### Monitoring

Watch logs in real-time:

```bash
tail -f logs/astravox.log
```

## 💾 Memory System

### SQLite Backend (Recommended)

```python
from ai_logic.memory import save_message_pair, get_history

# Save conversation
save_message_pair(conversation_id, user_msg, ai_msg)

# Retrieve history
history = get_history(conversation_id)
```

### Flexible Configuration

```bash
# Use SQLite (default)
MEMORY_BACKEND=sqlite

# Fallback to JSON
MEMORY_BACKEND=json
```

## 🔄 API Endpoints

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/message` | Send message, get complete response |
| POST | `/chat/stream` | Stream response in real-time |
| GET | `/chat/history/<conv_id>` | Get conversation history |
| GET | `/chat/health` | Health check |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login user |
| POST | `/auth/logout` | Logout user |
| GET | `/auth/status` | Check auth status |

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest 02-Backend/tests/ -v

# Specific test file
pytest 02-Backend/tests/test_utils.py -v

# With coverage
pytest 02-Backend/tests/ --cov=02-Backend --cov-report=html
```

### Test Structure

```python
# Unit tests
from utils.validators import validate_email

def test_email_validation():
    assert validate_email("valid@example.com") is True
    assert validate_email("invalid") is False

# Integration tests
def test_chat_endpoint(client):
    response = client.post('/chat/message', json={
        'message': 'Hello',
        'conversation_id': 'test-1'
    })
    assert response.status_code == 200
```

## 📈 Performance Tips

### Streaming

Use streaming for better UX with long responses:

```javascript
fetch('/chat/stream', {
    method: 'POST',
    body: JSON.stringify({
        message: 'Your message',
        conversation_id: 'conv-id'
    })
}).then(res => res.body.getReader())
  .then(reader => { /* stream chunks */ })
```

### Caching

The memory system automatically caches:
- Conversation history (SQLite)
- User preferences
- Recent interactions

### Rate Limiting

Configured per user:
- 200 requests per day
- 50 requests per hour
- Configured in `app.py`

## 🛠️ Development Workflow

### Add New Route

```python
# routes/custom_routes.py
from flask import Blueprint, request, jsonify
from utils.logger import app_logger
from utils.validators import require_json, require_fields

custom_bp = Blueprint('custom', __name__)

@custom_bp.route('/endpoint', methods=['POST'])
@require_json
@require_fields('field1', 'field2')
def my_endpoint():
    app_logger.info('Custom endpoint called')
    data = request.get_json()
    # ... implementation
    return jsonify({'status': 'OK'}), 200

# Register in app.py
app.register_blueprint(custom_bp, url_prefix='/custom')
```

### Add New Logger

```python
# In utils/logger.py
custom_logger = setup_logger("astravox.custom", "INFO")

# Use it
from utils.logger import custom_logger
custom_logger.info("Custom event")
```

### Add Tests

```python
# tests/test_custom.py
def test_my_feature(client):
    response = client.post('/custom/endpoint', json={...})
    assert response.status_code == 200
```

## 🚨 Troubleshooting

### Issue: "GEMINI_API_KEY not found"

```bash
# Check .env file exists and has key
cat .env | grep GEMINI_API_KEY

# Try setting it manually
export GEMINI_API_KEY=your-key
python main.py
```

### Issue: "Memory database not found"

```bash
# Initialize memory system
python -c "import ai_logic.memory_sql; ai_logic.memory_sql.init_memory_db()"
```

### Issue: "Rate limit exceeded"

- Check `RATE_LIMIT_PER_DAY` in `.env`
- Or increase limits in `app.py`
- User quotas reset daily

### Issue: "Database locked"

- Close other connections to `chat.db`
- Check for long-running queries
- Restart server if needed

## 📝 Best Practices

### Code Style

```python
# ✅ Good
def handle_message(user_message: str) -> dict:
    """Handle incoming message with validation."""
    try:
        clean_msg = sanitize_string(user_message)
        result = process_message(clean_msg)
        logger.info(f"Message processed: {conversation_id}")
        return result
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise

# ❌ Avoid
def handle_message(msg):
    result = process_message(msg)
    return result
```

### Error Handling

```python
# Always log and provide context
try:
    response = ai_engine.generate(prompt)
except TimeoutError as e:
    logger.warning(f"AI timeout for {conversation_id}")
    return {"status": "ERROR", "code": "AI_TIMEOUT"}
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return {"status": "ERROR", "code": "INTERNAL_ERROR"}
```

### Validation

```python
# Always validate before processing
if not validate_email(email):
    return jsonify({"error": "Invalid email"}), 400

if not 1 <= importance <= 5:
    logger.warning(f"Invalid importance: {importance}")
    importance = 1  # Use default
```

## 🔗 Related Documentation

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Gemini API Docs](https://ai.google.dev/)
- [SQLite Reference](https://www.sqlite.org/docs.html)
- [Pytest Guide](https://docs.pytest.org/)

## 📞 Support

For issues or questions:
1. Check logs in `logs/astravox.log`
2. Run tests to identify problems
3. Check `.env` configuration
4. Review error messages carefully

## 📅 Roadmap

### Phase 2 (Upcoming)
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Analytics and metrics
- [ ] User preferences persistence
- [ ] Rate limiting per user
- [ ] Database migrations

### Phase 3 (Future)
- [ ] Multi-model support
- [ ] Vector embeddings
- [ ] RAG system
- [ ] Voice integration
- [ ] Real-time collaboration

---

**Version**: 1.0.0  
**Last Modified**: 2026-06-07  
**Status**: ✅ Production Ready
