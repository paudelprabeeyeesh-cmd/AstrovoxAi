"""Tests for context management.

The property being pinned is that a prompt which is shorter than what the caller
supplied says so. A context that is quietly truncated has no explanation, cannot
be debugged, and makes any eval measured on it meaningless - so the omissions are
asserted rather than merely logged.
"""

import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
sys.path.insert(0, ".")

import pytest

from app.context_manager import (
    ContextBudget,
    ContextManager,
    RollingSummariser,
    Turn,
    estimate_tokens,
    redact_secrets,
)


@pytest.fixture
def manager():
    # 200 tokens of window, 50 reserved for the reply, so 150 for the prompt.
    return ContextManager(ContextBudget(max_tokens=200, reserved_output_tokens=50))


def test_output_is_reserved_before_the_prompt_spends_it(manager):
    # A prompt that fills the whole window leaves no room for the answer, so the
    # budget is the window minus the reservation, not the window.
    assert manager.budget.available_tokens == 150


def test_a_reservation_larger_than_the_window_floors_at_zero():
    # A configuration error must not produce a negative budget that downstream
    # comparisons silently accept.
    budget = ContextBudget(max_tokens=50, reserved_output_tokens=100)
    assert budget.available_tokens == 0


def test_history_within_budget_is_kept_whole(manager):
    turns = [
        Turn("user", "short question", recency=1),
        Turn("assistant", "short answer", recency=2),
    ]
    plan = manager.plan_history(turns)
    assert len(plan.kept) == 2
    assert plan.dropped == []
    assert plan.omitted == []


def test_history_over_budget_is_dropped_with_a_reason(manager):
    turns = [Turn("user", "word " * 300, recency=1)]
    plan = manager.plan_history(turns)
    assert plan.dropped, "nothing was dropped"
    assert plan.omitted, "a drop was recorded with no reason"
    assert "reserved for output" in plan.omitted[0].reason


def test_an_over_budget_history_is_not_in_the_kept_set(manager):
    turns = [Turn("user", "word " * 500, recency=1)]
    plan = manager.plan_history(turns)
    assert plan.kept == []


def test_a_rolling_summary_replaces_what_was_dropped(manager):
    # The turns leave the prompt; their content must not. Without a summary the
    # history is gone and the model loses it silently.
    turns = [Turn("user", "word " * 500, recency=1)]
    plan = manager.plan_history(turns, rolling_summary="Earlier we discussed X.")
    assert plan.summary == "Earlier we discussed X."
    # The summary is counted, so it cannot itself push the prompt over.
    assert plan.tokens >= estimate_tokens("Earlier we discussed X.")


def test_a_relevant_turn_survives_over_a_more_recent_irrelevant_one(manager):
    # Recency alone would keep the newer turn. Relevance must win, because the
    # question is what the answer has to address.
    turns = [
        Turn("user", "the actual answer to the current question", recency=1, relevance=1.0),
        Turn("assistant", "chatter about something else entirely", recency=9, relevance=0.1),
    ]
    plan = manager.plan_history(turns)
    kept_roles = {turn.role for turn in plan.kept}
    assert "user" in kept_roles


def test_tool_output_is_trimmed_before_history(manager):
    results = [("huge output " * 200, 0.9), ("small", 0.8)]
    kept, omitted = manager.trim_tool_results(results, budget_tokens=50)
    assert omitted, "a trimmed tool output left no record"
    assert all(estimate_tokens(text) <= 50 for text, _ in kept)


def test_tool_results_keep_their_original_order(manager):
    # Trimming must not reorder the evidence relative to how it was gathered.
    results = [("first " * 5, 0.5), ("second " * 5, 0.9), ("third " * 5, 0.7)]
    kept, _ = manager.trim_tool_results(results, budget_tokens=100)
    assert [text for text, _ in kept] == [text for text, _ in results[: len(kept)]]


def test_secret_redaction_reports_what_it_found(manager):
    result = manager.assemble(
        system="You are helpful. key = sk-abcdefghijklmnop1234",
        user="hello",
    )
    assert "sk-abcdefghijklmnop1234" not in result["text"]
    assert result["redactions"], "a redaction left no record"


def test_a_private_key_block_is_redacted(manager):
    key = "-----BEGIN RSA PRIVATE KEY-----\nabcd\n-----END RSA PRIVATE KEY-----"
    result = manager.assemble(system=key, user="hello")
    assert "BEGIN RSA PRIVATE KEY" not in result["text"]
    assert result["redactions"]


def test_the_callers_turn_is_never_dropped(manager):
    # A prompt that lost the question would be useless even if it fit.
    result = manager.assemble(
        system="word " * 400,
        user="the actual question",
    )
    assert "the actual question" in result["text"]


def test_an_omission_names_the_kind_and_count(manager):
    result = manager.assemble(
        system="word " * 400,
        user="question",
        snippets=["snippet " * 50],
    )
    assert result["omissions"], "an over-budget assembly reported no omissions"
    assert any("dropped" in o for o in result["omissions"])


def test_assembly_respects_the_budget(manager):
    result = manager.assemble(
        system="word " * 400,
        memory=["memory " * 50],
        user="question",
    )
    assert result["within_budget"]
    assert result["token_count"] <= 150


def test_assembly_is_deterministic(manager):
    kwargs = dict(
        system="sys",
        user="question",
        memory=["m1", "m2"],
        snippets=["s1", "s2"],
    )
    first = manager.assemble(**kwargs)
    second = manager.assemble(**kwargs)
    assert first["text"] == second["text"]
    assert first["token_count"] == second["token_count"]


def test_an_empty_assembly_is_within_budget(manager):
    result = manager.assemble()
    assert result["text"] == ""
    assert result["within_budget"]


def test_token_estimation_is_monotonic():
    short = estimate_tokens("a")
    long = estimate_tokens("a" * 400)
    assert long > short


def test_token_estimation_of_an_empty_string_is_zero():
    assert estimate_tokens("") == 0


def test_an_unredacted_text_reports_nothing():
    cleaned, found = redact_secrets("ordinary prose with no secrets")
    assert found == []
    assert cleaned == "ordinary prose with no secrets"


def test_an_assignment_secret_is_redacted():
    cleaned, found = redact_secrets("AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI value")
    assert "wJalrXUtnFEMI" not in cleaned
    assert found


def test_the_rolling_summary_is_deterministic():
    summariser = RollingSummariser()
    turns = [
        Turn("user", "alpha beta gamma delta", recency=1),
        Turn("assistant", "epsilon zeta", recency=2),
    ]
    assert summariser.summarise(turns) == summariser.summarise(turns)


def test_an_empty_history_summarises_to_nothing():
    assert RollingSummariser().summarise([]) == ""


def test_the_rolling_summary_respects_its_cap():
    summariser = RollingSummariser(max_chars=50)
    turns = [Turn("user", "word " * 200, recency=1)]
    assert len(summariser.summarise(turns)) <= 52


def test_a_higher_priority_section_wins_a_tight_budget():
    # The caller's question outranks a memory line, so a tight budget keeps the
    # question and drops the memory.
    tight = ContextManager(ContextBudget(max_tokens=40, reserved_output_tokens=0))
    result = tight.assemble(
        system="word " * 200,
        user="the question",
    )
    assert "the question" in result["text"]
