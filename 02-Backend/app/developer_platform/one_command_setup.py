"""One-command local setup."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)


def one_command_setup() -> dict[str, Any]:
    steps = []
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        steps.append({"step": "create_venv", "status": "ok"})
    except Exception as _e:  # noqa: BLE001
        steps.append({"step": "create_venv", "status": "failed", "error": str(_e)})
    try:
        subprocess.run([os.path.join("venv", "Scripts", "python"), "-m", "pip", "install", "-r", "02-Backend/requirements.txt"], check=True)
        steps.append({"step": "install_backend", "status": "ok"})
    except Exception as _e:  # noqa: BLE001
        steps.append({"step": "install_backend", "status": "failed", "error": str(_e)})
    try:
        os.chdir("apps/web")
        subprocess.run(["npm", "install"], check=True)
        steps.append({"step": "install_frontend", "status": "ok"})
    except Exception as _e:  # noqa: BLE001
        steps.append({"step": "install_frontend", "status": "failed", "error": str(_e)})
    return {"setup_steps": steps}
