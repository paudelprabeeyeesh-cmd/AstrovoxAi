"""
Serialization - Task 122

Stdlib-only serialization utilities for converting complex objects to/from JSON.
Handles dataclasses, datetimes, bytes (base64), sets, and nested structures.
"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any


class AstrovoxJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles common Python types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return {"__type__": "datetime", "value": obj.isoformat()}
        if isinstance(obj, bytes):
            return {"__type__": "bytes", "value": base64.b64encode(obj).decode("ascii")}
        if isinstance(obj, set):
            return {"__type__": "set", "value": list(obj)}
        if is_dataclass(obj) and not isinstance(obj, type):
            return {"__type__": "dataclass", "value": asdict(obj)}
        return super().default(obj)


class AstrovoxJSONDecoder(json.JSONDecoder):
    """Custom JSON decoder that restores special types."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, object_hook=self._object_hook, **kwargs)

    @staticmethod
    def _object_hook(obj: Any) -> Any:
        if not isinstance(obj, dict):
            return obj
        type_tag = obj.get("__type__")
        if type_tag == "datetime":
            return datetime.fromisoformat(obj["value"])
        if type_tag == "bytes":
            return base64.b64decode(obj["value"].encode("ascii"))
        if type_tag == "set":
            return set(obj["value"])
        if type_tag == "dataclass":
            return obj["value"]
        return obj


def serialize(obj: Any) -> str:
    """Serialize an object to a JSON string."""
    return json.dumps(obj, cls=AstrovoxJSONEncoder, sort_keys=True)


def deserialize(data: str) -> Any:
    """Deserialize a JSON string back to a Python object."""
    return json.loads(data, cls=AstrovoxJSONDecoder)


def serialize_to_bytes(obj: Any) -> bytes:
    """Serialize an object to UTF-8 encoded bytes."""
    return serialize(obj).encode("utf-8")


def deserialize_from_bytes(data: bytes) -> Any:
    """Deserialize UTF-8 encoded bytes back to a Python object."""
    return deserialize(data.decode("utf-8"))


def roundtrip(obj: Any) -> Any:
    """Serialize then deserialize to verify lossless encoding."""
    return deserialize(serialize(obj))
