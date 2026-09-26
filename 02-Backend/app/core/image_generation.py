"""
Image generation and understanding capabilities.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class GeneratedImage:
    url: str
    prompt: str
    width: int
    height: int
    model: str
    seed: Optional[int] = None


class ImageGenerationEngine:
    """Image generation engine."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.client = httpx.Client(timeout=120.0)
        self.default_model = "dall-e-3"

    def generate(self, prompt: str, width: int = 1024, height: int = 1024, model: Optional[str] = None, n: int = 1) -> List[GeneratedImage]:
        """Generate images from text prompt."""
        model = model or self.default_model
        if not self.api_key:
            return [GeneratedImage(url="", prompt=prompt, width=width, height=height, model=model, seed=0)]
        try:
            if model == "dall-e-3":
                return self._generate_dalle3(prompt, width, height, n)
            else:
                return self._generate_stable_diffusion(prompt, width, height, n)
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return []

    def _generate_dalle3(self, prompt: str, width: int, height: int, n: int) -> List[GeneratedImage]:
        """Generate using DALL-E 3."""
        url = "https://api.openai.com/v1/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": "dall-e-3", "prompt": prompt, "n": min(n, 1), "size": f"{width}x{height}"}
        response = self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return [GeneratedImage(url=item["url"], prompt=prompt, width=width, height=height, model="dall-e-3", seed=item.get("seed")) for item in data.get("data", [])]

    def _generate_stable_diffusion(self, prompt: str, width: int, height: int, n: int) -> List[GeneratedImage]:
        """Generate using Stable Diffusion."""
        return [GeneratedImage(url="", prompt=prompt, width=width, height=height, model="stable-diffusion")]

    def edit(self, image_path: str, prompt: str, mask_path: Optional[str] = None) -> List[GeneratedImage]:
        """Edit existing image."""
        return [GeneratedImage(url="", prompt=prompt, width=1024, height=1024, model="dall-e-2")]

    def variation(self, image_path: str, n: int = 1) -> List[GeneratedImage]:
        """Create variations of existing image."""
        return [GeneratedImage(url="", prompt="variation", width=1024, height=1024, model="dall-e-2")]


class ImageUnderstandingEngine:
    """Image understanding/analysis."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.client = httpx.Client(timeout=30.0)

    def analyze(self, image_url: str, question: str = "Describe this image") -> str:
        """Analyze image and answer question."""
        if not self.api_key:
            return "Image analysis requires API key"
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {"url": image_url}}]}],
                "max_tokens": 500,
            }
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return f"Error: {e}"


image_generation = ImageGenerationEngine()
image_understanding = ImageUnderstandingEngine()
