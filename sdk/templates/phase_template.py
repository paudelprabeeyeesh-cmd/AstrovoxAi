"""Phase template for SDK generation."""
from pathlib import Path

PHASE_TEMPLATE = """\
\"\"\"Phase {phase} — {name}
{description}
\"\"\"

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Phase{phase}Config:
    enabled: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class Phase{phase}Manager:
    def __init__(self):
        self._config = Phase{phase}Config()
        self._state: Dict[str, Any] = {{}}
        self._metrics: List[Dict[str, Any]] = []

    def initialize(self):
        logger.info("Phase {phase} — {name} initialized")

    def get_status(self) -> Dict[str, Any]:
        return {{
            "phase": {phase},
            "name": "{name}",
            "enabled": self._config.enabled,
            "uptime": time.time() - self._config.created_at,
        }}


phase_{phase} = Phase{phase}Manager()
"""


def generate_phase_file(phase: int, name: str, description: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"phase_{phase}.py"
    content = PHASE_TEMPLATE.format(phase=phase, name=name, description=description)
    file_path.write_text(content, encoding="utf-8")
    return file_path
