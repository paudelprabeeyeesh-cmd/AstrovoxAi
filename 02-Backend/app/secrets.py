import logging
import os
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .auth import role_required

logger = logging.getLogger(__name__)

_ASTROVOX_PREFIX = "ASTROVOX_"


class SecretManager:
    def __init__(self, prefix: str = _ASTROVOX_PREFIX, file_sink: Optional[str] = None):
        self.prefix = prefix
        self.file_sink = Path(file_sink) if file_sink else None
        self._entries: OrderedDict[str, dict] = OrderedDict()

    def load(self) -> Dict[str, str]:
        secrets: Dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                name = key[len(self.prefix):]
                secrets[name] = value
                self._entries[name] = {
                    "value": value,
                    "loaded_at": datetime.now(timezone.utc).isoformat(),
                    "source": "env",
                }
        return secrets

    def get(self, name: str) -> Optional[str]:
        return os.environ.get(f"{self.prefix}{name}")

    def rotate_secret(self, name: str, value: str) -> dict:
        key = f"{self.prefix}{name}"
        os.environ[key] = value
        entry = {
            "value": value,
            "rotated_at": datetime.now(timezone.utc).isoformat(),
            "source": "rotation",
        }
        self._entries[name] = entry
        if self.file_sink:
            try:
                self.file_sink.parent.mkdir(parents=True, exist_ok=True)
                with self.file_sink.open("a", encoding="utf-8") as f:
                    f.write(f"{name}\t{datetime.now(timezone.utc).isoformat()}\trotated\n")
            except OSError as exc:
                logger.warning("Secret rotation file sink failed: %s", exc)
        return entry

    def list_secrets(self) -> List[str]:
        return [key[len(self.prefix):] for key in os.environ if key.startswith(self.prefix)]


secret_manager = SecretManager()


class SecretRotationCheckResponse(BaseModel):
    secret: str
    last_rotated: Optional[str]
    source: str


router = APIRouter(tags=["admin-secrets"])


@router.get("/admin/secrets/rotation-check", response_model=List[SecretRotationCheckResponse])
async def rotation_check(_: str = Depends(role_required("admin"))):
    results = []
    for name in secret_manager.list_secrets():
        entry = secret_manager._entries.get(name, {"rotated_at": None, "source": "env"})
        results.append(
            SecretRotationCheckResponse(
                secret=name,
                last_rotated=entry.get("rotated_at") or entry.get("loaded_at"),
                source=entry.get("source", "env"),
            )
        )
    return results
