import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class PromptVersionManager:
    def __init__(self, prompts_dir: str = "app/prompts"):
        self.prompts_dir = prompts_dir
        self.versions = {}
        self._load_versions()

    def _load_versions(self):
        import os

        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir, exist_ok=True)
            return

        for filename in os.listdir(self.prompts_dir):
            if filename.endswith(".py"):
                prompt_name = filename[:-3]
                self.versions[prompt_name] = {"version": "1.0.0", "changelog": []}

    def get_prompt(self, name: str, version: str = None) -> str:
        if name not in self.versions:
            return ""

        prompt_file = os.path.join(self.prompts_dir, f"{name}.py")
        try:
            with open(prompt_file, "r") as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Failed to load prompt {name}: {e}")
            return ""

    def log_prompt_version(self, prompt_name: str, version: str, request_id: str):
        logger.info(f"PROMPT_VERSION: {prompt_name}={version} request_id={request_id}")
