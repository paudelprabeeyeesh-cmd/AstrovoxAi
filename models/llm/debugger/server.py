from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import torch
import torch.nn as nn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .inspector import ActivationViewer, GradientInspector, TokenInspector, WeightInspector
from .profiler import ComputeProfiler, MemoryProfiler, TokenProbabilityTracker
from .visualizer import AttentionMapVisualizer, GradientFlowVisualizer, HiddenStateVisualizer, KVCacheVisualizer

logger = logging.getLogger(__name__)


class DebugServer:
    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        debug_dir: str | None = None,
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.debug_dir = debug_dir or os.path.join(os.path.dirname(__file__), "static")
        os.makedirs(self.debug_dir, exist_ok=True)
        self._attention_viz = AttentionMapVisualizer()
        self._kv_viz = KVCacheVisualizer()
        self._hidden_viz = HiddenStateVisualizer()
        self._grad_viz = GradientFlowVisualizer()
        self._mem_profiler = MemoryProfiler()
        self._comp_profiler = ComputeProfiler()
        self._tok_tracker = TokenProbabilityTracker()
        self._activation_viewer = ActivationViewer()
        self._token_inspector = TokenInspector(getattr(model, "token_embedding", nn.Embedding(1, 1)))
        self._weight_inspector = WeightInspector()
        self._gradient_inspector = GradientInspector()
        self._connections: dict[str, list[WebSocket]] = {}
        self.app = FastAPI(title="Astrovox LLM Debugger", version="1.0.0")
        self._register_routes()

    def _register_routes(self) -> None:
        self.app.add_route("/static", self._serve_static_index, methods=["GET"])

        self.app.websocket("/ws/debug")(self._websocket_debug)

        class DebugStepRequest(BaseModel):
            prompt: str | None = Field(default=None, max_length=2048)
            token_id: int | None = Field(default=None, ge=0)
            param_name: str = Field(default="token_embedding.weight")

        @self.app.post("/api/debug/token")
        async def debug_token(req: DebugStepRequest):
            token_id = req.token_id if req.token_id is not None else 0
            info = self._token_inspector.inspect(token_id)
            return JSONResponse(self._token_inspector.to_dict(info))

        @self.app.get("/api/debug/weights")
        async def debug_weights():
            weights = []
            for name, param in self.model.named_parameters():
                weight = param.detach().cpu()
                weights.append(
                    {
                        "name": name,
                        "shape": list(weight.shape),
                        "norm": float(torch.norm(weight).item()),
                        "trainable": param.requires_grad,
                    }
                )
            return JSONResponse({"weights": weights})

        @self.app.get("/api/debug/weights/{param_name}")
        async def debug_weight_detail(param_name: str):
            info = self._weight_inspector.read(self.model, param_name)
            if info is None:
                return JSONResponse({"error": "not found"}, status_code=404)
            return JSONResponse(self._weight_inspector.to_dict(info))

        @self.app.post("/api/debug/forward")
        async def debug_forward():
            self._activation_viewer.register_hooks(self.model)
            self._mem_profiler.start()
            dummy = torch.zeros(1, 1, dtype=torch.long)
            with torch.no_grad():
                _ = self.model(dummy)
            results = []
            for layer in range(getattr(self.model, "num_hidden_layers", 1)):
                results.append(self._activation_viewer.read(layer))
            snap = self._mem_profiler.take_snapshot()
            return JSONResponse(
                {
                    "activations": [self._activation_viewer.to_dict(r) for r in results],
                    "memory": self._mem_profiler.summary(),
                }
            )

        @self.app.get("/api/debug/memory")
        async def debug_memory():
            return JSONResponse(self._mem_profiler.summary())

        @self.app.get("/api/debug/compute")
        async def debug_compute():
            return JSONResponse(self._comp_profiler.summary())

        @self.app.get("/api/debug/token-probabilities")
        async def debug_token_probabilities():
            return JSONResponse(self._tok_tracker.summary())

        @self.app.post("/api/debug/static")
        async def debug_static():
            path = os.path.join(self.debug_dir, "index.html")
            if not os.path.exists(path):
                return HTMLResponse("<h1>Static debugger UI not generated</h1>")
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(f.read())

    async def _websocket_debug(self, websocket: WebSocket) -> None:
        await websocket.accept()
        client_id = str(uuid.uuid4())
        self._connections.setdefault(client_id, []).append(websocket)
        self._mem_profiler.start()
        try:
            while True:
                msg = await websocket.receive_json()
                action = msg.get("action")
                payload = msg.get("payload", {})
                if action == "forward":
                    dummy = torch.zeros(1, 1, dtype=torch.long)
                    with torch.no_grad():
                        _ = self.model(dummy)
                    results = []
                    for layer in range(getattr(self.model, "num_hidden_layers", 1)):
                        results.append(self._activation_viewer.read(layer))
                    snap = self._mem_profiler.take_snapshot()
                    await websocket.send_json({"action": "forward", "data": results, "memory": snap})
                elif action == "memory":
                    snap = self._mem_profiler.take_snapshot()
                    await websocket.send_json({"action": "memory", "data": snap})
                elif action == "weights":
                    weights = []
                    for name, param in self.model.named_parameters():
                        weights.append(
                            {
                                "name": name,
                                "shape": list(param.shape),
                                "norm": float(torch.norm(param.detach().cpu()).item()),
                            }
                        )
                    await websocket.send_json({"action": "weights", "data": weights})
        except WebSocketDisconnect:
            pass
        finally:
            self._connections[client_id].remove(websocket)

    def _serve_static_index(self, path: str = "/static") -> JSONResponse:
        return JSONResponse({"status": "ok", "debugger": "static index placeholder"})


def create_debug_app(model: nn.Module, tokenizer: Any, debug_dir: str | None = None) -> FastAPI:
    server = DebugServer(model=model, tokenizer=tokenizer, debug_dir=debug_dir)
    return server.app
