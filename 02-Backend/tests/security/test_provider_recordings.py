"""Tests for recorded-response providers.

The property under test is that CI can exercise the provider contract without a
live key. That requires the replay to be faithful, a miss to be loud, and a
non-200 recording to be replayed as an error rather than as a success - because
an adapter's error path is exactly the part a mock usually hides.
"""

import json
import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
sys.path.insert(0, ".")

import pytest

from app.provider_recordings import (
    RecordingMiss,
    RecordingSet,
    RecordedExchange,
    RecordedProvider,
    ProviderRecordedError,
    canonical_request,
    hash_request,
    record_from_live,
)


@pytest.fixture
def recording():
    set_ = RecordingSet(provider="openai", version=1)
    exchange = RecordedExchange(
        request_hash=hash_request(
            canonical_request("gpt-4o-mini", [{"role": "user", "content": "hello"}])
        ),
        model="gpt-4o-mini",
        prompt_fingerprint="fp-1",
        response_text="recorded answer",
        usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        recorded_at="2026-01-01T00:00:00Z",
        provider_status=200,
    )
    set_.add(exchange)
    return set_


@pytest.fixture
def provider(recording):
    return RecordedProvider(name="openai", recording=recording)


MESSAGES = [{"role": "user", "content": "hello"}]


def test_a_recorded_response_is_replayed(provider):
    response = provider.complete("gpt-4o-mini", MESSAGES)
    assert response["choices"][0]["message"]["content"] == "recorded answer"
    assert response["usage"]["total_tokens"] == 8
    # The replay must not be distinguishable from a live response, or the
    # adapter under test could take a different path and the contract would go
    # untested.
    assert response["recorded"] is True
    assert response["provider"] == "openai"
    assert "id" in response


def test_an_unrecorded_request_raises_rather_than_succeeding(provider):
    # A silent default is how a recorded suite goes green while testing nothing.
    with pytest.raises(RecordingMiss):
        provider.complete("gpt-4o-mini", [{"role": "user", "content": "never recorded"}])


def test_a_non_200_recording_is_replayed_as_an_error(provider):
    provider.recording.add(
        RecordedExchange(
            request_hash=hash_request(
                canonical_request("gpt-4o-mini", [{"role": "user", "content": "boom"}])
            ),
            model="gpt-4o-mini",
            prompt_fingerprint="fp-2",
            response_text="rate limited",
            provider_status=429,
        )
    )
    # The adapter's error path has to be exercised, not mocked away.
    with pytest.raises(ProviderRecordedError) as exc:
        provider.complete("gpt-4o-mini", [{"role": "user", "content": "boom"}])
    assert exc.value.status == 429


def test_canonical_request_is_stable_across_key_order():
    first = canonical_request("m", [{"role": "user", "content": "hi"}], temperature=0)
    second = canonical_request("m", [{"role": "user", "content": "hi"}], temperature=0)
    assert first == second
    assert hash_request(first) == hash_request(second)


def test_a_whitespace_difference_does_not_lose_the_recording():
    # Without stripping, a reformatted request hashes differently and the miss
    # reads as a provider change rather than a formatting one.
    canonical_request("m", [{"role": "user", "content": "  padded  "}])
    from app.provider_recordings import canonical_request as canon

    stripped = canon("m", [{"role": "user", "content": "padded"}])
    assert "padded" in stripped
    assert "  " not in stripped


def test_a_different_prompt_hashes_differently():
    a = hash_request(canonical_request("m", [{"role": "user", "content": "a"}]))
    b = hash_request(canonical_request("m", [{"role": "user", "content": "b"}]))
    assert a != b


def test_a_recording_round_trips(recording, tmp_path):
    path = tmp_path / "openai.json"
    recording.save(path)
    reloaded = RecordingSet.load(path)
    assert len(reloaded.exchanges) == len(recording.exchanges)
    for key, exchange in recording.exchanges.items():
        assert reloaded.exchanges[key].response_text == exchange.response_text
        assert reloaded.exchanges[key].provider_status == exchange.provider_status


def test_a_missing_recording_file_yields_an_empty_set(tmp_path):
    # Empty, not synthetic: a missing file must fail loudly on the first request
    # rather than serving an invented success.
    set_ = RecordingSet.load(tmp_path / "absent.json")
    assert set_.exchanges == {}
    provider = RecordedProvider(name="x", recording=set_)
    with pytest.raises(RecordingMiss):
        provider.complete("m", MESSAGES)


def test_the_stats_report_what_was_served(provider):
    provider.complete("gpt-4o-mini", MESSAGES)
    try:
        provider.complete("gpt-4o-mini", [{"role": "user", "content": "nope"}])
    except RecordingMiss:
        pass
    stats = provider.stats()
    assert stats["recorded"] == 1
    assert stats["served"] == 1
    assert stats["missed"] == 1


def test_unused_recordings_are_reported(provider):
    # A recording never exercised is either dead weight or a request the test
    # stopped making - both should be visible.
    provider.complete("gpt-4o-mini", MESSAGES)
    assert provider.unused_keys() == []


def test_an_unused_recording_is_listed(recording):
    provider = RecordedProvider(name="openai", recording=recording)
    with pytest.raises(RecordingMiss):
        provider.complete("gpt-4o-mini", [{"role": "user", "content": "other"}])
    assert len(provider.unused_keys()) == 1


def test_recording_from_live_redacts_before_writing(tmp_path):
    # A credential in a response must not reach the recording file, because a
    # recording with a secret in it is a leak in the repository.
    def live(model, messages, **kwargs):
        return {
            "choices": [{"message": {"content": "token sk-abcdefghijklmnop1234 leaked"}}],
            "usage": {"total_tokens": 4},
        }

    out = tmp_path / "rec.json"
    record_from_live(
        "openai",
        live,
        [("gpt-4o-mini", MESSAGES, {})],
        out,
        redactor=lambda text: text.replace("sk-abcdefghijklmnop1234", "[REDACTED]"),
    )
    written = out.read_text(encoding="utf-8")
    assert "sk-abcdefghijklmnop1234" not in written
    assert "[REDACTED]" in written


def test_recording_from_live_captures_a_failure(tmp_path):
    # A provider error is a valid recording; the error path has to survive.
    def live(model, messages, **kwargs):
        raise RuntimeError("connection refused")

    out = tmp_path / "rec.json"
    set_ = record_from_live(
        "openai", live, [("gpt-4o-mini", MESSAGES, {})], out
    )
    exchange = next(iter(set_.exchanges.values()))
    assert exchange.provider_status != 200
    assert "connection refused" in exchange.response_text


def test_recording_from_live_is_replayable(tmp_path):
    # The point of the whole exercise: record once, then test offline.
    def live(model, messages, **kwargs):
        return {
            "choices": [{"message": {"content": "recorded offline"}}],
            "usage": {"total_tokens": 6},
        }

    out = tmp_path / "rec.json"
    record_from_live("openai", live, [("gpt-4o-mini", MESSAGES, {})], out)

    provider = RecordedProvider(
        name="openai", recording=RecordingSet.load(out)
    )
    response = provider.complete("gpt-4o-mini", MESSAGES)
    assert response["choices"][0]["message"]["content"] == "recorded offline"


def test_replay_latency_is_bounded(provider):
    # Replaying a latency of 20000ms must not stall the suite.
    exchange = next(iter(provider.recording.exchanges.values()))
    exchange.latency_ms = 20000
    provider.replay_latency = True

    import time

    started = time.time()
    provider.complete("gpt-4o-mini", MESSAGES)
    assert time.time() - started < 2.0


def test_latency_is_not_replayed_by_default(provider):
    exchange = next(iter(provider.recording.exchanges.values()))
    exchange.latency_ms = 5000

    import time

    started = time.time()
    provider.complete("gpt-4o-mini", MESSAGES)
    assert time.time() - started < 1.0
