import json
import logging
import os
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Any

import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, Field

from .engine import GenerationOutput, InferenceEngine, SamplingParams, _format_openai_chunk, _format_openai_response
from .scheduler import Request, RequestScheduler

logger = logging.getLogger(__name__)

REQUEST_COUNTER = Counter(
    "inference_requests_total", "Total inference requests", ["endpoint", "status"]
)
LATENCY_HISTOGRAM = Histogram("inference_latency_seconds", "Inference latency", ["endpoint"])


class CompletionRequest(BaseModel):
    prompt: str
    max_tokens: int = Field(default=100, ge=1, le=2048)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0)
    stop: list[str] | None = None
    stream: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    messages: list[ChatMessage]
    max_tokens: int = Field(default=100, ge=1, le=2048)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0)
    stop: list[str] | None = None
    stream: bool = False


class BatchRequest(BaseModel):
    prompts: list[str]
    max_tokens: int = Field(default=100, ge=1, le=2048)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0)


class InferenceServer:
    def __init__(self, engine: InferenceEngine, scheduler: RequestScheduler | None = None):
        self.engine = engine
        self.scheduler = scheduler or RequestScheduler()
        self.app = FastAPI(title="Astrovox Inference Engine", version="10.0.0")
        self._register_routes()

    def _register_routes(self) -> None:
        @self.app.get("/health")
        async def health():
            return {"status": "ok"}

        @self.app.post("/v1/completions")
        async def completions(req: CompletionRequest):
            with LATENCY_HISTOGRAM.labels("completions").time():
                params = SamplingParams(
                    max_new_tokens=req.max_tokens,
                    temperature=req.temperature,
                    top_k=req.top_k,
                    top_p=req.top_p,
                    repetition_penalty=req.repetition_penalty,
                    stop=req.stop,
                )
                try:
                    if req.stream:

                        async def _stream():
                            async for chunk in self.engine.astream_generate(req.prompt, params):
                                data = {"choices": [{"text": chunk, "index": 0}]}
                                yield _format_openai_chunk(data)
                            yield "data: [DONE]\n\n"

                        return StreamingResponse(_stream(), media_type="text/event-stream")
                    output = self.engine.generate(req.prompt, params)
                    REQUEST_COUNTER.labels("completions", "success").inc()
                    return _format_openai_response(output, prompt=req.prompt)
                except Exception as exc:
                    REQUEST_COUNTER.labels("completions", "error").inc()
                    raise HTTPException(status_code=500, detail=str(exc)) from exc

        @self.app.post("/v1/chat/completions")
        async def chat_completions(req: ChatCompletionRequest):
            with LATENCY_HISTOGRAM.labels("chat").time():
                params = SamplingParams(
                    max_new_tokens=req.max_tokens,
                    temperature=req.temperature,
                    top_k=req.top_k,
                    top_p=req.top_p,
                    repetition_penalty=req.repetition_penalty,
                    stop=req.stop,
                )
                messages = [m.model_dump() for m in req.messages]
                try:
                    if req.stream:

                        async def _stream():
                            async for chunk in self.engine.astream_generate(
                                "\n".join(f"{m['role']}: {m['content']}" for m in messages), params
                            ):
                                data = {"choices": [{"delta": {"content": chunk}, "index": 0}]}
                                yield _format_openai_chunk(data)
                            yield "data: [DONE]\n\n"

                        return StreamingResponse(_stream(), media_type="text/event-stream")
                    output = self.engine.chat(messages, params)
                    REQUEST_COUNTER.labels("chat", "success").inc()
                    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
                    return _format_openai_response(output, model="astrovox-chat", prompt=prompt)
                except Exception as exc:
                    REQUEST_COUNTER.labels("chat", "error").inc()
                    raise HTTPException(status_code=500, detail=str(exc)) from exc

        @self.app.post("/v1/batch")
        async def batch(req: BatchRequest):
            with LATENCY_HISTOGRAM.labels("batch").time():
                params = SamplingParams(
                    max_new_tokens=req.max_tokens,
                    temperature=req.temperature,
                    top_k=req.top_k,
                    top_p=req.top_p,
                    repetition_penalty=req.repetition_penalty,
                )
                try:
                    outputs = self.engine.batch_generate(req.prompts, params)
                    REQUEST_COUNTER.labels("batch", "success").inc()
                    return {
                        "results": [
                            {"text": o.text, "tokens": o.num_tokens, "latency_ms": o.latency_ms}
                            for o in outputs
                        ]
                    }
                except Exception as exc:
                    REQUEST_COUNTER.labels("batch", "error").inc()
                    raise HTTPException(status_code=500, detail=str(exc)) from exc

        @self.app.get("/metrics")
        async def metrics():
            from fastapi.responses import Response
            from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    def run(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        import uvicorn

        uvicorn.run(self.app, host=host, port=port, log_level="info")


def create_app(engine: InferenceEngine) -> FastAPI:
    server = InferenceServer(engine)
    return server.app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    engine: InferenceEngine | None = None,
) -> None:
    if engine is None:
        raise ValueError("engine must be provided")
    server = InferenceServer(engine)
    server.run(host=host, port=port)
