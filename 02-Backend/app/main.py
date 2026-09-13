from fastapi import FastAPI
from .cost import count_tokens
from .cache import cached
from .router import choose_model
from .fallback import safe_answer

app = FastAPI(title="AstrovoxAi", version="0.1.0")

@app.post("/solve")
async def solve(payload: dict):
    text = payload.get("text", "")
    model = choose_model("simple")
    tokens = count_tokens(text, model=model)
    result = cached(text, lambda t: {"echo": t, "model": model, "tokens": tokens})
    confidence = 0.9 if tokens < 50 else 0.6
    result["action"] = safe_answer(confidence)
    return result

@app.get("/health")
async def health():
    return {"status": "ok"}
