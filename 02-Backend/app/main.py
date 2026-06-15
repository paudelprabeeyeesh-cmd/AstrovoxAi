from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AstrovoxAi Engine",
    version="1.0.0",
    description="Production-grade asynchronous stateless backend"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health/readiness")
async def readiness_check():
    return {"status": "healthy"}