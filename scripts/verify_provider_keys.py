"""Verify provider keys work with one minimal call each.

Reads keys from .env via the app's own load_dotenv, so nothing is sourced from
the environment of this shell or echoed to a log. Prints only the HTTP status
and the first few characters of any reply body - never a key.
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "02-Backend"
sys.path.insert(0, str(BACKEND))
os.chdir(str(BACKEND))

from dotenv import load_dotenv

load_dotenv(dotenv_path=REPO / ".env", override=True)

import httpx


def redact(value):
    if not value:
        return "ABSENT"
    return "present (%d chars, starts %s...)" % (len(value), value[:6])


print("xai key        :", redact(os.getenv("XAI_API_KEY")))
print("openrouter key :", redact(os.getenv("OPENROUTER_API_KEY")))
print("openai key     :", redact(os.getenv("OPENAI_API_KEY")))
print("gemini key     :", redact(os.getenv("GEMINI_API_KEY")))
print()

results = {}


def check(label, url, headers, payload):
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
        body = response.text
        # Only a status and a short, non-secret fragment.
        results[label] = "HTTP %d | %s" % (response.status_code, body[:120].replace("\n", " "))
    except Exception as exc:
        results[label] = "ERROR %s: %s" % (type(exc).__name__, str(exc)[:120])


# One token each, to keep cost and rate-limit use minimal.
check(
    "openai",
    "https://api.openai.com/v1/chat/completions",
    {"Authorization": "Bearer " + (os.getenv("OPENAI_API_KEY") or "")},
    {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 3,
    },
)

check(
    "xai",
    "https://api.x.ai/v1/chat/completions",
    {"Authorization": "Bearer " + (os.getenv("XAI_API_KEY") or "")},
    {
        "model": "grok-3-mini",
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 3,
    },
)

check(
    "openrouter",
    "https://openrouter.ai/api/v1/chat/completions",
    {"Authorization": "Bearer " + (os.getenv("OPENROUTER_API_KEY") or "")},
    {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 3,
    },
)

check(
    "gemini",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    {"x-goog-api-key": os.getenv("GEMINI_API_KEY") or ""},
    {"contents": [{"parts": [{"text": "Reply with the single word: ok"}]}]},
)

check(
    "gemini-2.5-pro",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent",
    {"x-goog-api-key": os.getenv("GEMINI_API_KEY") or ""},
    {"contents": [{"parts": [{"text": "Reply with the single word: ok"}]}]},
)

for label in ("openai", "xai", "openrouter", "gemini"):
    print("%-11s %s" % (label, results.get(label, "not attempted")))
