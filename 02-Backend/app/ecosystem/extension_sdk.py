"""Extension SDK — stable interfaces for external developers."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SDKContext:
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: str = "http://localhost:8000"
    timeout: float = 30.0
    user_agent: str = "astrovox-extension-sdk/1.0"

    def sign(self, payload: Dict[str, Any]) -> str:
        secret = self.api_secret or os.getenv("ASTROVOX_SDK_SECRET", "")
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()


class PluginAPI(ABC):
    @abstractmethod
    def register(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def unregister(self, plugin_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def enable(self, plugin_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def disable(self, plugin_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def update(self, plugin_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
        ...


class WorkflowAPI(ABC):
    @abstractmethod
    def create(self, definition: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def execute(self, workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get_status(self, execution_id: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def cancel(self, execution_id: str) -> Dict[str, Any]:
        ...


class CompilerAPI(ABC):
    @abstractmethod
    def compile(self, source: str, target: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def validate(self, source: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def list_extension_points(self) -> Dict[str, Any]:
        ...


class RuntimeAPI(ABC):
    @abstractmethod
    def invoke(self, runtime: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def list_runtimes(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def health(self, runtime: str) -> Dict[str, Any]:
        ...


class StorageAPI(ABC):
    @abstractmethod
    def put(self, key: str, value: bytes, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get(self, key: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def delete(self, key: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def list_keys(self, prefix: str = "") -> Dict[str, Any]:
        ...


class EventAPI(ABC):
    @abstractmethod
    def publish(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def subscribe(self, event: str, handler: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def list_subscriptions(self) -> Dict[str, Any]:
        ...


class ExtensionSDK:
    """Facade over all extension APIs."""

    def __init__(self, context: SDKContext) -> None:
        self.context = context
        self.plugin = _StubPluginAPI(context)
        self.workflow = _StubWorkflowAPI(context)
        self.compiler = _StubCompilerAPI(context)
        self.runtime = _StubRuntimeAPI(context)
        self.storage = _StubStorageAPI(context)
        self.event = _StubEventAPI(context)

    def validate_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        required = ["name", "version", "entrypoint"]
        missing = [key for key in required if key not in manifest]
        if missing:
            return {"valid": False, "missing_fields": missing}
        return {"valid": True, "manifest": manifest}


class _StubPluginAPI(PluginAPI):
    def __init__(self, context: SDKContext) -> None:
        self._context = context

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "stub", "method": method, "path": path, "body": body}

    def register(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/ecosystem/plugins", manifest)

    def unregister(self, plugin_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/ecosystem/plugins/{plugin_id}")

    def enable(self, plugin_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/ecosystem/plugins/{plugin_id}/enable")

    def disable(self, plugin_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/ecosystem/plugins/{plugin_id}/disable")

    def update(self, plugin_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PUT", f"/ecosystem/plugins/{plugin_id}", manifest)


class _StubWorkflowAPI(WorkflowAPI):
    def __init__(self, context: SDKContext) -> None:
        self._context = context

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "stub", "method": method, "path": path, "body": body}

    def create(self, definition: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/ecosystem/workflows", definition)

    def execute(self, workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/ecosystem/workflows/{workflow_id}/execute", payload)

    def get_status(self, execution_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/ecosystem/workflows/executions/{execution_id}")

    def cancel(self, execution_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/ecosystem/workflows/executions/{execution_id}/cancel")


class _StubCompilerAPI(CompilerAPI):
    def __init__(self, context: SDKContext) -> None:
        self._context = context

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "stub", "method": method, "path": path, "body": body}

    def compile(self, source: str, target: str) -> Dict[str, Any]:
        return self._request("POST", "/ecosystem/compiler/compile", {"source": source, "target": target})

    def validate(self, source: str) -> Dict[str, Any]:
        return self._request("POST", "/ecosystem/compiler/validate", {"source": source})

    def list_extension_points(self) -> Dict[str, Any]:
        return self._request("GET", "/ecosystem/compiler/extension-points")


class _StubRuntimeAPI(RuntimeAPI):
    def __init__(self, context: SDKContext) -> None:
        self._context = context

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "stub", "method": method, "path": path, "body": body}

    def invoke(self, runtime: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/ecosystem/runtimes/{runtime}/invoke", payload)

    def list_runtimes(self) -> Dict[str, Any]:
        return self._request("GET", "/ecosystem/runtimes")

    def health(self, runtime: str) -> Dict[str, Any]:
        return self._request("GET", f"/ecosystem/runtimes/{runtime}/health")


class _StubStorageAPI(StorageAPI):
    def __init__(self, context: SDKContext) -> None:
        self._context = context

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "stub", "method": method, "path": path, "body": body}

    def put(self, key: str, value: bytes, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("POST", "/ecosystem/storage/objects", {"key": key, "metadata": metadata})

    def get(self, key: str) -> Dict[str, Any]:
        return self._request("GET", f"/ecosystem/storage/objects/{key}")

    def delete(self, key: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/ecosystem/storage/objects/{key}")

    def list_keys(self, prefix: str = "") -> Dict[str, Any]:
        return self._request("GET", "/ecosystem/storage/objects", {"prefix": prefix})


class _StubEventAPI(EventAPI):
    def __init__(self, context: SDKContext) -> None:
        self._context = context

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "stub", "method": method, "path": path, "body": body}

    def publish(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/ecosystem/events/publish", {"event": event, "payload": payload})

    def subscribe(self, event: str, handler: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        return self._request("POST", "/ecosystem/events/subscriptions", {"event": event})

    def list_subscriptions(self) -> Dict[str, Any]:
        return self._request("GET", "/ecosystem/events/subscriptions")
