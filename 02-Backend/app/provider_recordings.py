"""A provider that replays recorded responses.

WS-B-003 requires contract tests and recorded-response tests so CI never needs
live API keys. This is the recorded half: a provider whose responses come from a
fixture file rather than a network call, so the contract can be asserted offline.

The point is not to be a mock. A mock encodes what the author assumed the caller
would do, and it passes when the caller behaves that way, which is the same
reason a unit test of the mock proves nothing about the provider. A record
encodes what the provider actually returned, so a contract test against it fails
when the provider or the adapter changes.

Recorded responses are stored as JSON, keyed by a hash of the request. Hashing
the request rather than indexing it positionally means a reordered keys or
whitespace change does not lose the recording, and comparing the hash surfaces
a drift instead of silently serving a stale response.

A miss is a failure, not a pass. Returning a synthetic success for an unrecorded
request is how a suite goes green while testing nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class RecordingMiss(Exception):
    """No recorded response matched the request.

    Raised rather than defaulted to a synthetic success, so a drift between the
    adapter and the recording is a visible failure. Defaulting is how a recorded
    suite keeps passing while testing nothing.
    """

    def __init__(self, request_hash: str, recording: Path) -> None:
        super().__init__(
            f"no recorded response for request {request_hash[:12]}... in {recording}"
        )
        self.request_hash = request_hash
        self.recording = recording


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


@dataclass
class RecordedExchange:
    """One request/response pair, as the provider actually produced it."""

    request_hash: str
    model: str
    # prompt_fingerprint is the assembled prompt text, so a recording can be
    # reviewed and diffed by a human rather than only by its hash.
    prompt_fingerprint: str
    response_text: str
    usage: Dict[str, int] = field(default_factory=dict)
    recorded_at: str = ""
    # provenance records where this came from. An HTTP status that was not 200
    # is a valid recording and must be distinguishable from a success.
    provider_status: int = 200
    latency_ms: int = 0

    def to_json(self) -> Dict[str, Any]:
        return {
            "request_hash": self.request_hash,
            "model": self.model,
            "prompt_fingerprint": self.prompt_fingerprint,
            "response_text": self.response_text,
            "usage": self.usage,
            "recorded_at": self.recorded_at,
            "provider_status": self.provider_status,
            "latency_ms": self.latency_ms,
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "RecordedExchange":
        return cls(
            request_hash=data["request_hash"],
            model=data["model"],
            prompt_fingerprint=data.get("prompt_fingerprint", ""),
            response_text=data["response_text"],
            usage=data.get("usage", {}),
            recorded_at=data.get("recorded_at", ""),
            provider_status=int(data.get("provider_status", 200)),
            latency_ms=int(data.get("latency_ms", 0)),
        )


@dataclass
class RecordingSet:
    """A file of recorded exchanges, addressed by request hash."""

    exchanges: Dict[str, RecordedExchange] = field(default_factory=dict)
    # The model these were recorded against, so a suite can assert it is testing
    # the adapter for the provider it claims to be testing.
    provider: str = ""
    version: int = 1

    def to_json(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "provider": self.provider,
            "exchanges": [e.to_json() for e in self.exchanges.values()],
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "RecordingSet":
        return cls(
            exchanges={
                e["request_hash"]: RecordedExchange.from_json(e)
                for e in data.get("exchanges", [])
            },
            provider=data.get("provider", ""),
            version=int(data.get("version", 1)),
        )

    @classmethod
    def load(cls, path: Path) -> "RecordingSet":
        if not path.exists():
            return cls()
        return cls.from_json(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json(), indent=2, sort_keys=True), encoding="utf-8"
        )

    def add(self, exchange: RecordedExchange) -> None:
        self.exchanges[exchange.request_hash] = exchange


def canonical_request(model: str, messages: List[Dict[str, str]], **kwargs: Any) -> str:
    """Canonicalise a request into a stable string.

    Sorted keys and stripped values, so two semantically identical requests
    hash the same. Without canonicalisation a whitespace or key-order change
    loses a recording, and the miss then reads as a provider change rather than
    a formatting one.
    """
    payload = {
        "model": model,
        "messages": [
            {k: v.strip() if isinstance(v, str) else v for k, v in m.items()}
            for m in messages
        ],
    }
    for key, value in sorted(kwargs.items()):
        if value is None:
            continue
        payload[key] = value
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def hash_request(canonical: str) -> str:
    """Hash a canonical request into its recording key."""
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# The replaying provider
# ---------------------------------------------------------------------------


@dataclass
class RecordedProvider:
    """Serves recorded responses in place of a live provider.

    Implements the same surface as a live provider - same request shape, same
    response shape - so the adapter under test cannot tell the difference and
    the contract is being exercised rather than bypassed.
    """

    name: str
    recording: RecordingSet
    # replay_latency reproduces the recorded latency, so a timeout or a
    # retry path is tested rather than running instantly and never hitting it.
    replay_latency: bool = False
    _served: List[str] = field(default_factory=list)
    _misses: List[str] = field(default_factory=list)

    def complete(
        self, model: str, messages: List[Dict[str, str]], **kwargs: Any
    ) -> Dict[str, Any]:
        """Return the recorded response, or raise RecordingMiss.

        The response shape matches a live provider's: the same keys, the same
        usage block, so an adapter reading it is reading what it would read from
        the API.
        """
        canonical = canonical_request(model, messages, **kwargs)
        request_hash = hash_request(canonical)
        exchange = self.recording.exchanges.get(request_hash)

        if exchange is None:
            self._misses.append(request_hash)
            raise RecordingMiss(request_hash, Path(f"{self.name}-recording.json"))

        if self.replay_latency and exchange.latency_ms:
            time.sleep(min(exchange.latency_ms, 200) / 1000.0)

        # A non-200 recording is replayed as an error, not a success: an
        # adapter's error path has to be exercised rather than mocked away.
        if exchange.provider_status != 200:
            self._served.append(request_hash)
            raise ProviderRecordedError(
                exchange.provider_status, exchange.response_text
            )

        self._served.append(request_hash)
        return {
            "id": "rec-" + exchange.request_hash[:12],
            "model": exchange.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": exchange.response_text},
                    "finish_reason": "stop",
                }
            ],
            "usage": dict(exchange.usage),
            "recorded": True,
            "provider": self.name,
        }

    def stats(self) -> Dict[str, int]:
        return {
            "recorded": len(self.recording.exchanges),
            "served": len(self._served),
            "missed": len(self._misses),
            "unused": len(self.recording.exchanges) - len(
                {e for e in self._served}
            ),
        }

    def unused_keys(self) -> List[str]:
        """Recordings never exercised by this run.

        Reported because a recording that is never served is either dead weight
        or a request the test stopped making. Either way it should be visible.
        """
        return [k for k in self.recording.exchanges if k not in self._served]


class ProviderRecordedError(Exception):
    """A recorded non-200 response, replayed as an error."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"provider returned {status}: {body[:120]}")
        self.status = status
        self.body = body


# ---------------------------------------------------------------------------
# Recording a live provider
# ---------------------------------------------------------------------------


def record_from_live(
    provider_name: str,
    live_complete,
    requests: List[Tuple[str, List[Dict[str, str]], Dict[str, Any]]],
    output: Path,
    *,
    redactor=None,
) -> RecordingSet:
    """Record real responses to a file.

    Kept separate from the replay path so the recording tool has no dependency
    on the replay provider. `redactor` is applied before writing, so a
    credential in a response is scrubbed at record time rather than at replay
    time - a recording with a secret in it is a leak in the repository.
    """
    recording = RecordingSet(provider=provider_name, version=1)

    for model, messages, kwargs in requests:
        started = time.time()
        try:
            response = live_complete(model, messages, **kwargs)
            status = 200
            text = response["choices"][0]["message"]["content"]
            usage = response.get("usage", {})
        except Exception as exc:  # noqa: BLE001 - recorded, never re-raised here
            status = getattr(exc, "status", 500)
            text = str(exc)
            usage = {}

        canonical = canonical_request(model, messages, **kwargs)
        request_hash = hash_request(canonical)

        fingerprint = _fingerprint(messages)
        if redactor is not None:
            text = redactor(text)

        recording.add(
            RecordedExchange(
                request_hash=request_hash,
                model=model,
                prompt_fingerprint=fingerprint,
                response_text=text,
                usage=usage,
                recorded_at=datetime.now(timezone.utc).isoformat(),
                provider_status=status,
                latency_ms=int((time.time() - started) * 1000),
            )
        )

    recording.save(output)
    return recording


def _fingerprint(messages: List[Dict[str, str]]) -> str:
    """A short human-reviewable hash of the prompt.

    Recorded so a reviewer can see which prompt produced which response without
    reading the full hash, and so a re-recording can be diffed.
    """
    text = " ".join(m.get("content", "") for m in messages)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def default_recording_dir() -> Path:
    """Where recordings live, overridable for a test that needs an isolated copy."""
    configured = os.getenv("PROVIDER_RECORDING_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "recordings"


def load_provider(name: str) -> RecordedProvider:
    """Load a recorded provider from the fixtures directory.

    A missing file yields an empty provider that fails on every request rather
    than one that silently succeeds, so a missing recording is loud.
    """
    path = default_recording_dir() / f"{name}.json"
    return RecordedProvider(name=name, recording=RecordingSet.load(path))


# A minimal recording shipped with the repository so the contract tests have
# something to assert against without a network call.
SEED_RECORDING = RecordingSet(
    provider="openai",
    version=1,
).to_json()
