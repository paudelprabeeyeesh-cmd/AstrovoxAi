"""SDK generator for multiple languages."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GeneratedSDK:
    language: str
    version: str
    files: Dict[str, str]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SDKGenerator:
    def __init__(self) -> None:
        self._generated: List[GeneratedSDK] = []

    def generate(self, language: str, api_spec: Dict[str, Any], version: str = "v1") -> GeneratedSDK:
        files = {f"{language}_client.{language}": f"# Generated {language} SDK for AstrovoxAI"}
        sdk = GeneratedSDK(language=language, version=version, files=files)
        self._generated.append(sdk)
        return sdk

    def get_generated(self) -> List[GeneratedSDK]:
        return list(self._generated)


sdk_generator = SDKGenerator()
