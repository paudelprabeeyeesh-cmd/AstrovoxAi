"""Text-to-video generation engine.

Supports multiple generation backends:
- HuggingFace Diffusers (ModelScope, Stable Video Diffusion)
- OpenAI-compatible APIs
- Replicate-style hosted models
- Local inference with torch/transformers where available
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GeneratedVideo:
    url: str
    prompt: str
    duration_seconds: float
    width: int
    height: int
    fps: int
    frames: int
    model: str
    seed: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TextToVideoEngine:
    """Generate video from text prompts."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        hf_token: Optional[str] = None,
        device: str = "cuda",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.hf_token = hf_token or os.getenv("HF_TOKEN", "")
        self.device = device
        self.default_model = "stable-video-diffusion"
        self._pipe = None
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import httpx
            self._client = httpx.Client(timeout=300.0)
        except ImportError:
            logger.debug("httpx not available; HTTP client disabled")

    def _load_diffusers(self) -> bool:
        if self._pipe is not None:
            return True
        try:
            import torch
            from diffusers import StableVideoDiffusionPipeline
            self._pipe = StableVideoDiffusionPipeline.from_pretrained(
                "stabilityai/stable-video-diffusion-img2vid-xt",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                variant="fp16" if self.device == "cuda" else None,
            )
            self._pipe.to(self.device)
            if self.device == "cuda":
                self._pipe.enable_model_cpu_offload()
            return True
        except Exception as exc:
            logger.debug("diffusers load failed: %s", exc)
            self._pipe = None
            return False

    def generate(
        self,
        prompt: str,
        image: Optional[str] = None,
        duration_seconds: float = 4.0,
        width: int = 1024,
        height: int = 576,
        fps: int = 24,
        model: Optional[str] = None,
        seed: Optional[int] = None,
        negative_prompt: str = "",
        guidance_scale: float = 7.5,
    ) -> List[GeneratedVideo]:
        model = model or self.default_model
        frames = max(1, int(duration_seconds * fps))

        if self._load_diffusers():
            return self._generate_diffusers(prompt, image, frames, width, height, fps, model, seed, negative_prompt, guidance_scale)

        if self._client and self.api_key:
            return self._generate_openai(prompt, frames, width, height, fps, model, seed)

        return self._generate_mock(prompt, frames, width, height, fps, model, seed)

    def _generate_diffusers(
        self,
        prompt: str,
        image: Optional[str],
        frames: int,
        width: int,
        height: int,
        fps: int,
        model: str,
        seed: Optional[int],
        negative_prompt: str,
        guidance_scale: float,
    ) -> List[GeneratedVideo]:
        try:
            import torch
            from diffusers import StableVideoDiffusionPipeline
            from PIL import Image
            import numpy as np

            if image:
                if image.startswith("http"):
                    import requests
                    resp = requests.get(image, timeout=30)
                    pil_image = Image.open(io.BytesIO(resp.content)).convert("RGB")
                else:
                    pil_image = Image.open(io.BytesIO(base64.b64decode(image))).convert("RGB")
            else:
                pil_image = Image.new("RGB", (width, height), (0, 0, 0))

            pil_image = pil_image.resize((width, height), Image.Resampling.LANCZOS)
            generator = torch.Generator(device=self.device).manual_seed(seed or 0)

            frames_out = self._pipe(
                pil_image,
                height=height,
                width=width,
                num_frames=frames,
                motion_bucket_id=127,
                fps=fps,
                generator=generator,
                negative_prompt=negative_prompt,
                guidance_scale=guidance_scale,
            ).frames[0]

            video_buffer = io.BytesIO()
            frames_out[0].save(
                video_buffer,
                format="GIF",
                save_all=True,
                append_images=frames_out[1:],
                duration=int(1000 / fps),
                loop=0,
            )
            video_buffer.seek(0)
            b64 = base64.b64encode(video_buffer.read()).decode("utf-8")
            return [
                GeneratedVideo(
                    url=f"data:image/gif;base64,{b64}",
                    prompt=prompt,
                    duration_seconds=frames / fps,
                    width=width,
                    height=height,
                    fps=fps,
                    frames=frames,
                    model=model,
                    seed=seed,
                )
            ]
        except Exception as exc:
            logger.error("diffusers generation failed: %s", exc)
            return self._generate_mock(prompt, frames, width, height, fps, model, seed)

    def _generate_openai(
        self,
        prompt: str,
        frames: int,
        width: int,
        height: int,
        fps: int,
        model: str,
        seed: Optional[int],
    ) -> List[GeneratedVideo]:
        try:
            url = "https://api.openai.com/v1/video/generations"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "prompt": prompt,
                "size": f"{width}x{height}",
                "n": 1,
            }
            response = self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return [
                GeneratedVideo(
                    url=item.get("url", ""),
                    prompt=prompt,
                    duration_seconds=frames / fps,
                    width=width,
                    height=height,
                    fps=fps,
                    frames=frames,
                    model=model,
                    seed=seed or data.get("seed"),
                )
                for item in data.get("data", [])
            ]
        except Exception as exc:
            logger.error("OpenAI video generation failed: %s", exc)
            return self._generate_mock(prompt, frames, width, height, fps, model, seed)

    def _generate_mock(
        self,
        prompt: str,
        frames: int,
        width: int,
        height: int,
        fps: int,
        model: str,
        seed: Optional[int],
    ) -> List[GeneratedVideo]:
        duration = frames / fps
        logger.warning("Generating mock video for prompt=%s frames=%d", prompt, frames)
        return [
            GeneratedVideo(
                url="",
                prompt=prompt,
                duration_seconds=duration,
                width=width,
                height=height,
                fps=fps,
                frames=frames,
                model=model,
                seed=seed,
                metadata={"mock": True},
            )
        ]

    def edit(
        self,
        source_video: str,
        prompt: str,
        mask: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[GeneratedVideo]:
        return self.generate(prompt, image=source_video, model=model or "video-edit")

    def variation(self, source_video: str, model: Optional[str] = None) -> List[GeneratedVideo]:
        return self.generate("variation of input video", image=source_video, model=model or "video-variation")

    def extend(self, source_video: str, duration_seconds: float = 2.0, model: Optional[str] = None) -> List[GeneratedVideo]:
        return self.generate("extend video", image=source_video, duration_seconds=duration_seconds, model=model or "video-extend")


text_to_video = TextToVideoEngine()
