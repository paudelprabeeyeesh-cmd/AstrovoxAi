"""Static analysis gate."""
from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class StaticAnalysisGate:
    def run(self) -> dict[str, Any]:
        results = {"critical": 0, "high": 0, "medium": 0}
        try:
            subprocess.check_output(["bandit", "-r", "02-Backend/app", "-ll"], stderr=subprocess.STDOUT, text=True)
        except FileNotFoundError:
            results["critical"] = -1
        except subprocess.CalledProcessError:
            results["critical"] = 1
        return results
