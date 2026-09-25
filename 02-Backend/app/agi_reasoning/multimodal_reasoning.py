import logging
from typing import Any

logger = logging.getLogger(__name__)


class MultimodalReasoningService:
    def fuse(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"fused": True, "modalities": list(inputs.keys())}
