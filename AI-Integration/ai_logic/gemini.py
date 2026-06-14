import os
import time
from typing import Generator

from dotenv import load_dotenv, find_dotenv

try:
    from google import genai
except Exception:
    genai = None


def _load_env_from_hierarchy() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        current_dir,
        os.path.dirname(current_dir),
        os.path.dirname(os.path.dirname(current_dir)),
    ]
    for candidate in candidates:
        env_path = os.path.join(candidate, ".env")
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
            return
    try:
        load_dotenv(find_dotenv())
    except Exception:
        pass


class GeminiEngine:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        _load_env_from_hierarchy()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.client = None

        if not self.api_key:
            print("[gemini] WARN: GEMINI_API_KEY not found in environment. AI requests will fallback or fail safely.")
            return

        if genai is None:
            print("[gemini] WARN: google.genai SDK not installed.")
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as exc:
            print(f"[gemini] ERROR: Failed to instantiate GenAI client: {exc}")
            self.client = None

    def generate_stream(self, user_prompt: str, **kwargs) -> Generator[str, None, None]:
        if not self.client:
            yield "[gemini] Service unavailable. Configure GEMINI_API_KEY and install google-generativeai."
            return

        try:
            response = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=user_prompt,
                **({} if not kwargs else kwargs),
            )
            for chunk in response:
                text = getattr(chunk, "text", None) or getattr(chunk, "output", None)
                if text:
                    yield text
        except Exception as exc:
            yield f"[gemini] Error generating response: {exc}"

    def generate(self, user_prompt: str, timeout: float = 20.0, **kwargs) -> str:
        pieces = []
        start = time.time()
        for chunk in self.generate_stream(user_prompt, **kwargs):
            pieces.append(chunk)
            if time.time() - start > timeout:
                pieces.append("\n[gemini] Response truncated due to timeout.")
                break
        return "".join(pieces)


def get_ai_stream(user_prompt: str, **kwargs) -> Generator[str, None, None]:
    engine = GeminiEngine()
    yield from engine.generate_stream(user_prompt, **kwargs)


def get_ai_response(user_prompt: str, **kwargs) -> str:
    engine = GeminiEngine()
    return engine.generate(user_prompt, **kwargs)
