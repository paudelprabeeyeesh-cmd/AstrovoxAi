"""FastAPI application for LLM serving."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from llm.router import router as llm_router
from training.routes import router as training_router
from fine_tune.router import router as fine_tune_router
from model_management.router import router as model_management_router

app = FastAPI(
    title="AstrovoxAI LLM Service",
    version="1.0.0",
    description="LLM inference API for AstrovoxAI",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(llm_router)
app.include_router(training_router)
app.include_router(fine_tune_router)
app.include_router(model_management_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
