# AstrovoxAI

FastAPI backend for AstrovoxAI. Multi-provider LLM router with Groq, Gemini, Mistral, OpenRouter, and HuggingFace.

## Setup

```powershell
cd C:\AstrovoxAi\02-Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
uvicorn app.main:app --reload
```

## Deploy

Render free tier. Set env vars in dashboard:
- `ASTROVOX_DB` = `/tmp/astrovox.db`
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `MISTRAL_API_KEY`
- `OPENROUTER_API_KEY`
- `HF_API_KEY`

## Tests

```powershell
pytest tests/ -v
```
