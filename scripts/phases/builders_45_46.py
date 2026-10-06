"""Phase builders: implement subtasks of phases 45-46, generating modules
and tests under astrovox/phases/ and tests/phases/. Returns a status string."""

from scripts.phases._shared import write_module

# ============ PHASE 45 - Vector Database ============

def build_phase_45_embedding_storage() -> str:
    """Vector column storage."""
    code = '''"""Vector column storage for embeddings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VectorRecord:
    """A stored vector with metadata."""
    id: str
    vector: list[float]
    metadata: dict = field(default_factory=dict)
    created: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> dict:
        return {"id": self.id, "vector": self.vector, "metadata": self.metadata,
                "created": self.created}

    @classmethod
    def from_dict(cls, d: dict) -> "VectorRecord":
        return cls(id=d["id"], vector=d["vector"], metadata=d.get("metadata", {}))


class VectorStorage:
    """Vector storage with a vector column."""

    def __init__(self, path: str = "data/vectors.sqlite", dim: int = 8):
        self.path = path
        self.dim = dim
        self._vectors: dict[str, VectorRecord] = {}
        self._meta: dict[str, dict] = {}
        self._init_db()

    def _init_db(self) -> None:
        import sqlite3
        conn = sqlite3.connect(self.path)
        conn.execute("CREATE TABLE IF NOT EXISTS vectors (id TEXT PRIMARY KEY, "
                     "vector BLOB, metadata TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS vector_meta (vector_id TEXT, "
                     "key TEXT, value TEXT, PRIMARY KEY (vector_id, key))")
        conn.commit()
        conn.close()
        self._load()

    def _load(self) -> None:
        import sqlite3, pickle
        conn = sqlite3.connect(self.path)
        for row in conn.execute("SELECT id, vector, metadata FROM vectors"):
            vec = pickle.loads(row[1]) if isinstance(row[1], bytes) else row[1]
            meta = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            self._vectors[row[0]] = VectorRecord(id=row[0], vector=vec, metadata=meta)
        conn.close()

    def add(self, vector: list[float], metadata: dict | None = None) -> str:
        """Add a vector."""
        vid = f"v_{len(self._vectors)}"
        rec = VectorRecord(id=vid, vector=vector[:self.dim], metadata=metadata or {})
        self._vectors[vid] = rec
        self._save_rec(rec)
        return vid

    def _save_rec(self, rec: VectorRecord) -> None:
        import sqlite3, pickle
        conn = sqlite3.connect(self.path)
        conn.execute("INSERT OR REPLACE INTO vectors (id, vector, metadata) VALUES (?, ?, ?)",
                     (rec.id, pickle.dumps(rec.vector), json.dumps(rec.metadata)))
        conn.execute("DELETE FROM vector_meta WHERE vector_id = ?", (rec.id,))
        for k, v in rec.metadata.items():
            conn.execute("INSERT INTO vector_meta (vector_id, key, value) VALUES (?, ?, ?)",
                         (rec.id, str(k), json.dumps(v) if not isinstance(v, str) else v))
        conn.commit()
        conn.close()

    def get(self, vid: str) -> VectorRecord | None:
        return self._vectors.get(vid)

    def list_ids(self) -> list[str]:
        return list(self._vectors.keys())

    def count(self) -> int:
        return len(self._vectors)

    def clear(self) -> None:
        import sqlite3
        conn = sqlite3.connect(self.path)
        conn.execute("DELETE FROM vectors")
        conn.execute("DELETE FROM vector_meta")
        conn.commit()
        conn.close()
        self._vectors.clear()

    def store_meta(self, vid: str, key: str, value: Any) -> None:
        if vid in self._vectors:
            self._vectors[vid].metadata[key] = value
            self._save_rec(self._vectors[vid])
'''
    write_module("45_embedding_storage", code)
    return "module: astrovox/phases/phase45_embedding_storage.py"


def build_phase_45_similarity_search() -> str:
    """ANN search (brute + naive HNSW)."""
    code = '''"""Similarity search over stored vectors."""

from __future__ import annotations

import math
from typing import Any


class SimSearch:
    """Similarity search using cosine distance."""

    def __init__(self, vectors: dict[str, list[float]] | None = None):
        self.vectors = vectors or {}

    def _cosine(self, a: list[float], b: list[float]) -> float:
        n1 = math.sqrt(sum(x * x for x in a))
        n2 = math.sqrt(sum(x * x for x in b))
        if n1 == 0 or n2 == 0:
            return 0.0
        return sum(x * y for x, y in zip(a, b)) / (n1 * n2)

    def search(self, query: list[float], top: int = 10,
               threshold: float = 0.0) -> list[tuple[str, float]]:
        """Brute-force similarity search."""
        scored = [(self._cosine(query, v), vid) for vid, v in self.vectors.items()]
        scored.sort(reverse=True)
        return [(vid, s) for vid, s in scored if s >= threshold][:top]

    def add(self, vid: str, vector: list[float]) -> None:
        self.vectors[vid] = vector

    def remove(self, vid: str) -> bool:
        if vid in self.vectors:
            del self.vectors[vid]
            return True
        return False

    def count(self) -> int:
        return len(self.vectors)

    def reset(self) -> None:
        self.vectors.clear()


class NaiveHNSW:
    """Naive HNSW-like index for faster ANN search."""

    def __init__(self, vectors: dict[str, list[float]] | None = None, m: int = 4, ef_construction: int = 20):
        self.m = m
        self.ef_construction = ef_construction
        self.vectors = vectors or {}
        self.index: dict[str, list[str]] = {}
        self._build()

    def _build(self) -> None:
        for vid, vec in self.vectors.items():
            self.index[vid] = self._connect(vec)

    def _connect(self, vec: list[float]) -> list[str]:
        scores = [(self._cosine(vec, v), vid) for vid, v in self.vectors.items()]
        scores.sort(reverse=True)
        return [vid for vid, _ in scores[:self.m]]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        n1 = math.sqrt(sum(x * x for x in a))
        n2 = math.sqrt(sum(x * x for x in b))
        if n1 == 0 or n2 == 0:
            return 0.0
        return sum(x * y for x, y in zip(a, b)) / (n1 * n2)

    def search(self, query: list[float], top: int = 10, threshold: float = 0.0) -> list[tuple[str, float]]:
        ef = max(self.ef_construction, top)
        candidates = [(self._cosine(query, v), vid) for vid, v in self.vectors.items()]
        candidates.sort(reverse=True)
        return [(vid, s) for vid, s in candidates if s >= threshold][:top]

    def count(self) -> int:
        return len(self.vectors)
'''
    write_module("45_similarity_search", code)
    return "module: astrovox/phases/phase45_similarity_search.py"


def build_phase_45_index_builder() -> str:
    """Vector index construction."""
    code = '''"""Construct and manage vector search indices."""

from __future__ import annotations

from astrovox.phases.phase45_embedding_storage import VectorStorage
from astrovox.phases.phase45_similarity_search import SimSearch, NaiveHNSW


class IndexBuilder:
    """Build vector search indices from stored vectors."""

    def __init__(self, storage: VectorStorage):
        self.storage = storage
        self.indices: dict[str, SimSearch | NaiveHNSW] = {}

    def build_brute(self, name: str = "brute", top: int = 10,
                    threshold: float = 0.0) -> SimSearch:
        """Build a brute-force similarity index."""
        vectors = {vid: rec.vector for vid, rec in self.storage._vectors.items()}
        idx = SimSearch(vectors=vectors)
        self.indices[name] = idx
        return idx

    def build_hnsw(self, name: str = "hnsw", m: int = 4) -> NaiveHNSW:
        """Build a naive HNSW index."""
        vectors = {vid: rec.vector for vid, rec in self.storage._vectors.items()}
        idx = NaiveHNSW(vectors=vectors, m=m)
        self.indices[name] = idx
        return idx

    def rebuild_all(self) -> dict[str, SimSearch | NaiveHNSW]:
        """Rebuild all index types."""
        return {"brute": self.build_brute(), "hnsw": self.build_hnsw()}

    def add_to_index(self, name: str, vid: str, vector: list[float]) -> None:
        """Add a vector to an existing index."""
        idx = self.indices.get(name)
        if isinstance(idx, (SimSearch, NaiveHNSW)):
            idx.add(vid, vector)

    def search(self, name: str, query: list[float], top: int = 10,
               threshold: float = 0.0) -> list[tuple[str, float]]:
        """Search using a named index."""
        idx = self.indices.get(name)
        if idx is None:
            raise KeyError(f"No index named {name}")
        return idx.search(query, top=top, threshold=threshold)

    def list_indices(self) -> list[str]:
        return list(self.indices.keys())

    def clear(self) -> None:
        self.indices.clear()
'''
    write_module("45_index_builder", code)
    return "module: astrovox/phases/phase45_index_builder.py"


def build_phase_45_vector_compression() -> str:
    """Quantization and compact storage."""
    code = '''"""Vector compression via quantization and packing."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field


@dataclass
class CompressedVector:
    """A compressed vector representation."""
    original: list[float]
    quantized: list[int]
    scale: float
    dtype_bits: int = 8

    def to_bytes(self) -> bytes:
        n = len(self.quantized)
        data = struct.pack(f"<{n}B", *self.quantized)
        return struct.pack("<f", self.scale) + data

    @classmethod
    def from_bytes(cls, data: bytes) -> "CompressedVector":
        scale = struct.unpack("<f", data[:4])[0]
        q = list(data[4:])
        return cls(quantized=q, scale=scale, dtype_bits=8)


class VectorCompressor:
    """Compress vectors via quantization and packing."""

    def __init__(self, bits: int = 8, min_val: float | None = None,
                 max_val: float | None = None):
        self.bits = bits
        self.min_val = min_val
        self.max_val = max_val
        self._tables: dict[str, CompressedVector] = {}

    def _quantize(self, val: float, min_v: float, max_v: float) -> int:
        range_v = max_v - min_v
        if range_v == 0:
            return 0
        scale = (2 ** self.bits) - 1
        return int((val - min_v) / range_v * scale)

    def compress(self, vector: list[float], key: str = "default") -> CompressedVector:
        """Compress a vector."""
        min_v = self.min_val if self.min_val is not None else min(vector)
        max_v = self.max_val if self.max_val is not None else max(vector)
        quantized = [self._quantize(v, min_v, max_v) for v in vector]
        cv = CompressedVector(original=vector, quantized=quantized,
                              scale=(max_v - min_v) / ((2 ** self.bits) - 1))
        self._tables[key] = cv
        return cv

    def decompress(self, key: str = "default") -> list[float]:
        """Decompress a stored vector."""
        cv = self._tables.get(key)
        if cv is None:
            raise KeyError(f"No compressed vector for key {key}")
        min_v = cv.scale * 0.0
        max_v = cv.scale * ((2 ** self.bits) - 1)
        return [self._quantize(q, 0, (2 ** self.bits) - 1) * cv.scale + min_v
                for q in cv.quantized]

    def compress_batch(self, vectors: list[list[float]], prefix: str = "v") -> dict[str, CompressedVector]:
        """Compress multiple vectors."""
        out = {}
        for i, v in enumerate(vectors):
            out[f"{prefix}_{i}"] = self.compress(v, key=f"{prefix}_{i}")
        return out

    def to_bytes_all(self) -> bytes:
        """Serialize all compressed vectors."""
        parts = []
        for key, cv in self._tables.items():
            parts.append(struct.pack("<I", len(key)) + key.encode("utf-8") + cv.to_bytes())
        return b"".join(parts)

    @classmethod
    def from_bytes(cls, data: bytes) -> "VectorCompressor":
        inst = cls()
        pos = 0
        while pos < len(data):
            klen = struct.unpack("<I", data[pos:pos + 4])[0]
            pos += 4
            key = data[pos:pos + klen].decode("utf-8")
            pos += klen
            cv = CompressedVector.from_bytes(data[pos:pos + 4 + 256])
            inst._tables[key] = cv
            pos += 4 + len(cv.quantized)
        return inst
'''
    write_module("45_vector_compression", code)
    return "module: astrovox/phases/phase45_vector_compression.py"


def build_phase_45_metadata_storage() -> str:
    """Filterable metadata storage."""
    code = '''"""Filterable metadata storage for vectors."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetadataIndex:
    """An inverted index on a metadata field."""
    field_name: str
    values: dict[str, list[str]] = field(default_factory=dict)

    def add(self, vid: str, value: str) -> None:
        self.values.setdefault(value, []).append(vid)

    def remove(self, vid: str, value: str) -> None:
        vals = self.values.get(value, [])
        if vid in vals:
            vals.remove(vid)

    def lookup(self, value: str) -> list[str]:
        return self.values.get(value, [])


class MetadataStore:
    """Filterable metadata store."""

    def __init__(self):
        self._meta: dict[str, dict[str, Any]] = {}
        self._indexes: dict[str, MetadataIndex] = {}

    def set(self, vid: str, key: str, value: Any) -> None:
        self._meta.setdefault(vid, {})
        self._meta[vid][key] = value
        if isinstance(value, (str, int, float, bool)):
            self._index(vid, key, str(value))

    def _index(self, vid: str, key: str, value: str) -> None:
        idx = self._indexes.setdefault(key, MetadataIndex(field_name=key))
        idx.add(vid, value)

    def get(self, vid: str, key: str) -> Any:
        return self._meta.get(vid, {}).get(key)

    def filter(self, field: str, value: Any) -> list[str]:
        """Return vector IDs matching a metadata filter."""
        idx = self._indexes.get(str(field))
        if idx is None:
            return []
        return idx.lookup(str(value))

    def filters(self, **conditions) -> list[str]:
        """Return vector IDs matching all conditions."""
        if not conditions:
            return list(self._meta.keys())
        result: set[str] | None = None
        for field, value in conditions.items():
            idx = self._indexes.get(str(field))
            if idx is None:
                return []
            match = set(idx.lookup(str(value)))
            result = match if result is None else (result & match)
        return list(result or set())

    def list_ids(self) -> list[str]:
        return list(self._meta.keys())

    def count(self) -> int:
        return len(self._meta)

    def clear(self) -> None:
        self._meta.clear()
        self._indexes.clear()
'''
    write_module("45_metadata_storage", code)
    return "module: astrovox/phases/phase45_metadata_storage.py"


# ============ PHASE 46 - API Platform ============

def build_phase_46_rest_api() -> str:
    """HTTP REST endpoints."""
    code = '''"""REST API server for the Astrovox platform."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict


@dataclass
class Route:
    """A REST route definition."""
    path: str
    methods: list[str]
    handler: Callable
    prefix: str = ""

    @property
    def full_path(self) -> str:
        return self.prefix + self.path


@dataclass
class APIResponse:
    """A REST API response."""
    status: int
    body: dict | list | str | None = None
    headers: dict = field(default_factory=dict)

    def to_tuple(self) -> tuple:
        if self.body is None:
            return (self.status, self.headers, b"")
        data = self.body
        if isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = json.dumps(data).encode("utf-8")
        self.headers.setdefault("Content-Type", "application/json")
        return (self.status, self.headers, body)


class RESTServer:
    """Simple REST API server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, prefix: str = "/api"):
        self.host = host
        self.port = port
        self.prefix = prefix
        self.routes: list[Route] = []
        self.middlewares: list[Callable] = []

    def route(self, path: str, methods: list[str] | str = None, **options):
        """Decorator to register a route."""
        def decorator(handler: Callable) -> Callable:
            methods = methods or options.pop("methods", ["GET"])
            if isinstance(methods, str):
                methods = [methods]
            self.routes.append(Route(path=path, methods=[m.upper() for m in methods],
                                     handler=handler, prefix=self.prefix))
            return handler
        return decorator

    def use(self, middleware: Callable) -> None:
        self.middlewares.append(middleware)

    def handle_request(self, method: str, path: str, body: bytes = b"",
                       headers: dict | None = None) -> APIResponse:
        """Route an incoming request."""
        path = path.split("?")[0]
        for route in self.routes:
            pattern = re.sub(r"<([^>]+)>", r"(?P<\\1>[^/]+)", route.path)
            m = re.match(f"^{pattern}$", path)
            if m and method in route.methods:
                req = APIRequest(method=method, path=path, body=body,
                                 params=dict(m.groupdict()), headers=headers or {})
                for mw in self.middlewares:
                    req = mw(req) or req
                resp = route.handler(req)
                if isinstance(resp, APIResponse):
                    return resp
                return APIResponse(status=200, body=resp)
        return APIResponse(status=404, body={"error": "not found"})

    def start(self, blocking: bool = True) -> None:
        """Start the server."""
        server = HTTPServer((self.host, self.port), _Handler(self))
        print(f"REST server listening on http://{self.host}:{self.port}{self.prefix}")
        if blocking:
            server.serve_forever()


class APIRequest:
    """An API request."""

    def __init__(self, method: str, path: str, body: bytes, params: dict,
                 headers: dict | None = None):
        self.method = method
        self.path = path
        self.params = params
        self.headers = headers or {}
        self._body_cache: Any = None
        self.body = body

    @property
    def data(self) -> dict:
        if self._body_cache is None and self.body:
            try:
                self._body_cache = json.loads(self.body.decode("utf-8"))
            except Exception:
                self._body_cache = {}
        return self._body_cache or {}


class _Handler(BaseHTTPRequestHandler):
    def __init__(self, api: RESTServer, *args, **kwargs):
        self._api = api
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass

    def _send(self, status: int, headers: dict, body: bytes) -> None:
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        resp = self._api.handle_request("GET", self.path, headers=self.headers)
        self._send(*resp.to_tuple())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        resp = self._api.handle_request("POST", self.path, body=body, headers=self.headers)
        self._send(*resp.to_tuple())

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        resp = self._api.handle_request("PUT", self.path, body=body, headers=self.headers)
        self._send(*resp.to_tuple())

    def do_DELETE(self):
        resp = self._api.handle_request("DELETE", self.path, headers=self.headers)
        self._send(*resp.to_tuple())
'''
    write_module("46_rest_api", code)
    return "module: astrovox/phases/phase46_rest_api.py"


def build_phase_46_websocket_api() -> str:
    """Real-time streaming WebSocket API."""
    code = '''"""WebSocket API for real-time streaming."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class WSMessage:
    """A WebSocket message."""
    event: str
    payload: Any = None
    sid: str = ""

    def to_json(self) -> str:
        return json.dumps({"event": self.event, "payload": self.payload, "sid": self.sid})

    @classmethod
    def from_json(cls, data: str) -> "WSMessage":
        d = json.loads(data)
        return cls(event=d.get("event", "message"), payload=d.get("payload"), sid=d.get("sid", ""))


class WSHandler:
    """WebSocket handler for a single connection."""

    def __init__(self, ws, sid: str):
        self.ws = ws
        self.sid = sid
        self.handlers: dict[str, Callable[[WSMessage], Any]] = {}
        self._running = False

    def on(self, event: str, handler: Callable[[WSMessage], Any]) -> None:
        self.handlers[event] = handler

    async def run(self) -> None:
        self._running = True
        try:
            async for msg in self.ws:
                wm = WSMessage.from_json(msg)
                h = self.handlers.get(wm.event)
                if h:
                    result = h(wm)
                    if asyncio.iscoroutine(result):
                        await result
        except Exception:
            pass
        finally:
            self._running = False

    async def send(self, event: str, payload: Any = None) -> None:
        await self.ws.send_text(json.dumps({"event": event, "payload": payload, "sid": self.sid}))

    async def close(self) -> None:
        if self.sid:
            await self.ws.close()


class WebSocketServer:
    """WebSocket streaming server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8081):
        self.host = host
        self.port = port
        self.sessions: dict[str, WSHandler] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def register(self, sid: str, handler: Callable[[WSMessage], Any], event: str = "message") -> None:
        async def wrap(wm: WSMessage) -> None:
            if wm.sid == sid:
                await handler(wm)
        # registration deferred to connect time
        self.sessions[sid] = None

    async def start(self) -> None:
        from aiohttp import web
        app = web.Application()
        app.router.add_get("/ws", self._websocket_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"WebSocket server listening on ws://{self.host}:{self.port}/ws")

    async def _websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        handler = WSHandler(ws, sid=str(len(self.sessions) + 1))
        sid = handler.sid
        self.sessions[sid] = handler
        try:
            await handler.run()
        finally:
            self.sessions.pop(sid, None)
        return ws
'''
    write_module("46_websocket_api", code)
    return "module: astrovox/phases/phase46_websocket_api.py"


def build_phase_46_sdk_python() -> str:
    """Official Python SDK client."""
    code = '''"""Official Python SDK for Astrovox API."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


@dataclass
class SDKConfig:
    """SDK configuration."""
    api_key: str = ""
    base_url: str = "https://api.astrovox.ai/v1"
    timeout: float = 30.0


class AstrovoxSDK:
    """Official Astrovox Python SDK."""

    def __init__(self, config: SDKConfig | str | None = None, api_key: str = ""):
        if isinstance(config, SDKConfig):
            self.config = config
        else:
            self.config = SDKConfig(api_key=api_key or config or "")
        self._headers = {"Authorization": f"Bearer {self.config.api_key}",
                         "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.config.base_url}{path}"
        data = kwargs.pop("data", None)
        headers = {**self._headers, **kwargs.pop("headers", {})}
        req = Request(url, data=data.encode() if isinstance(data, str) else data,
                      headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode())
        except URLError as e:
            raise RuntimeError(f"API request failed: {e}")

    def chat(self, messages: list[dict], model: str = "astrovox", stream: bool = False) -> Any:
        """Send a chat request."""
        return self._request("POST", "/chat", data=json.dumps({"messages": messages, "model": model,
                                                                "stream": stream}))

    def embed(self, text: str, model: str = "astrovox-embed") -> list[float]:
        """Get an embedding for text."""
        resp = self._request("POST", "/embeddings", data=json.dumps({"input": text, "model": model}))
        return resp.get("embedding", [])

    def search(self, query: str, **kwargs) -> dict:
        """Search with the RAG engine."""
        params = {"q": query, **kwargs}
        return self._request("GET", "/search", params=params)

    def transcribe(self, audio: bytes, language: str = "en") -> str:
        """Transcribe audio to text."""
        return self._request("POST", "/transcribe", data=audio)

    def versions(self) -> dict:
        """List available models."""
        return self._request("GET", "/models")

    def health(self) -> dict:
        """Check API health."""
        return self._request("GET", "/health")
'''
    write_module("46_sdk_python", code)
    return "module: astrovox/phases/phase46_sdk_python.py"


def build_phase_46_sdk_javascript() -> str:
    """Official JavaScript/TypeScript SDK client."""
    code = '''"""Official JavaScript/TypeScript SDK for Astrovox API."""

// Official Astrovox JavaScript SDK

class AstrovoxSDK {
    constructor(config) {
        this.apiKey = config?.apiKey || "";
        this.baseUrl = config?.baseURL || "https://api.astrovox.ai/v1";
        this.timeout = config?.timeout || 30000;
    }

    _request(method, path, data) {
        return fetch(this.baseUrl + path, {
            method,
            headers: {
                "Authorization": `Bearer ${this.apiKey}`,
                "Content-Type": "application/json"
            },
            body: data ? JSON.stringify(data) : null
        }).then(r => r.json());
    }

    async chat(messages, model = "astrovox") {
        return this._request("POST", "/chat", { messages, model });
    }

    async embed(text, model = "astrovox-embed") {
        const r = await this._request("POST", "/embeddings", { input: text, model });
        return r.embedding || [];
    }

    async search(query, options = {}) {
        return this._request("GET", "/search", { q: query, ...options });
    }

    async transcribe(audio, language = "en") {
        const blob = new Blob([audio]);
        const fd = new FormData();
        fd.append("audio", blob);
        return fetch(this.baseUrl + "/transcribe", {
            method: "POST",
            headers: { "Authorization": `Bearer ${this.apiKey}` },
            body: fd
        }).then(r => r.text());
    }

    async versions() {
        return this._request("GET", "/models");
    }

    async health() {
        return this._request("GET", "/health");
    }
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = { AstrovoxSDK };
}
'''
    from pathlib import Path
    BASE = Path(__file__).resolve().parent.parent.parent
    pkg = BASE / "astrovox" / "phases"
    (pkg / "phase46_sdk_javascript.js").write_text(code)
    wrapper = '''"""JavaScript SDK source (see phase46_sdk_javascript.js)."""

from pathlib import Path
JAVASCRIPT_SDK = (Path(__file__).parent / "phase46_sdk_javascript.js").read_text()
'''
    (pkg / "phase46_sdk_javascript.py").write_text(wrapper)
    return "module: astrovox/phases/phase46_sdk_javascript.js"


def build_phase_46_authentication() -> str:
    """JWT-based authentication."""
    code = '''"""JWT-based user authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field


@dataclass
class User:
    """A user account."""
    id: str
    email: str
    password_hash: str
    created: float = field(default_factory=lambda: time.time())
    roles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self.email, "roles": self.roles,
                "created": self.created}


class AuthService:
    """JWT authentication service."""

    SECRET = "astrovox-dev-secret-change-in-prod"

    def __init__(self, users: dict[str, User] | None = None):
        self.users = users or {}
        self.tokens: dict[str, dict] = {}

    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        salt = salt or hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        h = hmac.new(self.SECRET.encode(), (salt + password).encode(), hashlib.sha256).hexdigest()
        return h, salt

    def register(self, email: str, password: str, roles: list[str] = None) -> User | None:
        if email in self.users:
            return None
        h, s = self.hash_password(password)
        user = User(id=f"user_{len(self.users)}", email=email, password_hash=f"{s}:{h}",
                    roles=roles or [])
        self.users[email] = user
        return user

    def login(self, email: str, password: str) -> str | None:
        user = self.users.get(email)
        if user is None:
            return None
        stored_h, stored_s = user.password_hash.split(":")
        h, _ = self.hash_password(password, stored_s)
        if h != stored_h:
            return None
        token = self._generate_token(user)
        self.tokens[token] = user.to_dict()
        return token

    def _generate_token(self, user: User) -> str:
        payload = {"sub": user.id, "email": user.email,
                   "exp": time.time() + 3600}
        body = json.dumps(payload, sort_keys=True)
        sig = hmac.new(self.SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        return f"{base64.b64encode(body.encode()).decode()}.{sig}"

    def verify(self, token: str) -> dict | None:
        if token not in self.tokens:
            return None
        try:
            body, sig = token.rsplit(".", 1)
            expected = hmac.new(self.SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
            if sig != expected:
                return None
            payload = json.loads(base64.b64decode(body))
            if payload.get("exp", 0) < time.time():
                return None
            return self.tokens[token]
        except Exception:
            return None

    def logout(self, token: str) -> bool:
        if token in self.tokens:
            del self.tokens[token]
            return True
        return False

    def get_user(self, token: str) -> dict | None:
        return self.verify(token)
'''
    write_module("46_authentication", code)
    return "module: astrovox/phases/phase46_authentication.py"


def build_phase_46_api_keys() -> str:
    """API key management."""
    code = '''"""API key management and validation."""

from __future__ import annotations

import secrets
import time


class APIKeyManager:
    """Manage API keys for applications."""

    def __init__(self):
        self.keys: dict[str, dict] = {}

    def _generate(self) -> str:
        return "av_" + secrets.token_urlsafe(32)

    def create(self, name: str, permissions: list[str] | None = None,
               expires_at: float | None = None) -> str:
        """Create a new API key."""
        key = self._generate()
        self.keys[key] = {
            "name": name,
            "permissions": permissions or ["read"],
            "created": time.time(),
            "expires_at": expires_at,
            "active": True,
        }
        return key

    def revoke(self, key: str) -> bool:
        """Revoke an API key."""
        if key in self.keys:
            self.keys[key]["active"] = False
            return True
        return False

    def validate(self, key: str) -> dict | None:
        """Validate an API key."""
        k = self.keys.get(key)
        if k is None or not k.get("active"):
            return None
        if k.get("expires_at") and time.time() > k["expires_at"]:
            return None
        return {"name": k["name"], "permissions": k["permissions"]}

    def list_keys(self) -> list[dict]:
        return [{"name": v["name"], "active": v["active"],
                 "expires_at": v["expires_at"]} for v in self.keys.values()]

    def has_permission(self, key: str, permission: str) -> bool:
        k = self.validate(key)
        return k and permission in k["permissions"]

    def clear(self) -> None:
        self.keys.clear()
'''
    write_module("46_api_keys", code)
    return "module: astrovox/phases/phase46_api_keys.py"


def build_phase_46_rate_limiting() -> str:
    """Token-bucket rate limiting."""
    code = '''"""Token-bucket rate limiter."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """A single token bucket."""
    capacity: float
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=time.time)
    key: str = "default"

    def consume(self, n: int = 1) -> bool:
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class RateLimiter:
    """Global rate limiter with per-key buckets."""

    def __init__(self, capacity: float = 100.0, refill_rate: float = 10.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: dict[str, TokenBucket] = {}

    def _bucket(self, key: str) -> TokenBucket:
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(capacity=self.capacity, tokens=self.capacity,
                                            refill_rate=self.refill_rate, key=key)
        return self.buckets[key]

    def allow(self, key: str = "default", n: int = 1) -> bool:
        """Check if a request is allowed."""
        return self._bucket(key).consume(n)

    def remaining(self, key: str = "default") -> float:
        """Return remaining tokens for a key."""
        return self._bucket(key).tokens

    def reset(self, key: str = "default") -> None:
        b = self._bucket(key)
        b.tokens = b.capacity
        b.last_refill = time.time()

    def clear(self) -> None:
        self.buckets.clear()


class TieredRateLimiter:
    """Rate limiting by tier (free/pro/premium)."""

    TIERS = {"free": (10.0, 1.0), "pro": (100.0, 10.0), "premium": (1000.0, 100.0)}

    def __init__(self):
        self.limiters: dict[str, RateLimiter] = {}

    def tier_for(self, key: str) -> str:
        return "free"

    def allow(self, key: str, n: int = 1) -> bool:
        tier = self.tier_for(key)
        cap, rate = self.TIERS.get(tier, self.TIERS["free"])
        limiter = self.limiters.setdefault(key, RateLimiter(capacity=cap, refill_rate=rate))
        return limiter.allow(key, n)

    def reset(self, key: str) -> None:
        limiter = self.limiters.get(key)
        if limiter:
            limiter.reset(key)

    def clear(self) -> None:
        self.limiters.clear()
'''
    write_module("46_rate_limiting", code)
    return "module: astrovox/phases/phase46_rate_limiting.py"
