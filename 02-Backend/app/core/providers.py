from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Provider:
    name: str
    base_url: str
    env_key: str
    default_model: str

PROVIDERS: List[Provider] = [
    Provider(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        env_key="GROQ_API_KEY",
        # Llama 3.3 is Groq's current free default and is highly reliable.
        default_model="llama-3.3-70b-versatile",
    ),
    Provider(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        env_key="GEMINI_API_KEY",
        # Gemini 2.5 Flash is the free tier workhorse. It replaced 2.0 Flash.
        default_model="gemini-2.5-flash",
    ),
    Provider(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        env_key="MISTRAL_API_KEY",
        # This is correct; the rate limit error is temporary.
        default_model="mistral-small-latest",
    ),
    Provider(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        env_key="OPENROUTER_API_KEY",
        # The OpenRouter free tier has rotated. A stable, free option is Gemma 4.
        default_model="google/gemma-4-26b-a4b-it:free",
    ),
    Provider(
        name="huggingface",
        base_url="https://router.huggingface.co/v1",
        env_key="HF_API_KEY",
        # Keep the model, but be aware the free tier has tight permission limits.
        default_model="meta-llama/Llama-3.1-8B-Instruct",
    ),
]