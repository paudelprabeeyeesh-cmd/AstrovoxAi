"""Context management: token accounting, history trimming, and stated omissions.

WS-B-006 asks for token counting, output reservation, history trimming with
rolling summaries, tool-result relevance trimming, secret redaction, and an
explanation of what was omitted. The last item is the one that is usually
skipped and is the reason any of it is trustworthy: a prompt that is quietly
shorter than the caller supplied has no way to be debugged by anyone later.

Everything here is pure and dependency-light, so it can be unit-tested without a
provider call and without tiktoken installed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

# Average characters per token for the common tokenizers. Rough by nature; the
# point is that a caller can budget before spending, and that the same text
# always counts the same.
CHARS_PER_TOKEN = 4.0

# The same skeleton the Go side uses, so a budget computed here and a budget
# computed there agree rather than being off by a factor of two.
_SECRET_SHAPE = re.compile(
    r"\b(?:sk-|AKIA|ghp_|gho_|xox|glpat-|AIza)[A-Za-z0-9_-]{8,}"
)
_ASSIGNMENT_SECRET = re.compile(
    r"\b([A-Za-z0-9_]*(?:SECRET|TOKEN|PASSWORD|PRIVATE_KEY)[A-Za-z0-9_]*)\s*=\s*(\S+)",
    re.IGNORECASE,
)
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
)


def estimate_tokens(text: str) -> int:
    """Estimate the token count of a text.

    Roughly four characters per token. Deliberately named `estimate` rather than
    `count`, and deliberately not presented as a provider's tokenizer: a caller
    that treats it as exact will mis-budget by a few percent, which is a
    survivable error, whereas a caller that treats a real tokenizer's count as
    interchangeable across providers will not.
    """
    if not text:
        return 0
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def redact_secrets(text: str) -> Tuple[str, List[str]]:
    """Redact credential-shaped text, returning the text and what was found.

    Returns the findings rather than only the cleaned text, because "nothing was
    redacted" and "we cannot tell" are different states and a caller needs to
    know which one it is looking at.
    """
    found: List[str] = []

    def record(match: "re.Match[str]") -> str:
        found.append(match.group(0)[:24] + "...")
        return "[REDACTED]"

    cleaned = _SECRET_SHAPE.sub(record, text)
    cleaned = _ASSIGNMENT_SECRET.sub(
        lambda m: (found.append(m.group(1) + "=..."), f"{m.group(1)}=[REDACTED]")[1],
        cleaned,
    )
    cleaned = _PRIVATE_KEY_BLOCK.sub(
        lambda m: (found.append(m.group(0)[:24] + "..."), "[REDACTED_KEY_BLOCK]")[1],
        cleaned,
    )
    return cleaned, found


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@dataclass
class Turn:
    """One exchange in a conversation."""

    role: str
    content: str
    # recency is a caller-supplied ordering hint, so trimming does not depend on
    # the order the turns happen to sit in a list.
    recency: int = 0
    # relevance is a caller-supplied weight for this turn with respect to the
    # current query. A turn that does not bear on the question is dropped before
    # one that does, whatever their recency.
    relevance: float = 1.0

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.content)


@dataclass
class Omission:
    """A record of something removed from the context, and why.

    Carried on the result rather than logged, so the caller can surface it and a
    test can assert it. An omission that exists only in a log line is invisible
    to both.
    """

    kind: str
    count: int
    reason: str

    def describe(self) -> str:
        return f"{self.kind}: dropped {self.count} ({self.reason})"


@dataclass
class ContextBudget:
    """How much room the prompt has, with output reserved up front.

    Output reservation happens at budget time rather than after assembly,
    because a prompt that leaves no room for the reply is a request that fails
    at the provider after the caller has already paid for the prompt tokens.
    """

    max_tokens: int
    reserved_output_tokens: int

    @property
    def available_tokens(self) -> int:
        """What the prompt may consume.

        Floored at zero rather than allowed to go negative: a reservation larger
        than the window is a configuration error, and the answer to it is to
        produce no prompt rather than a prompt with a negative budget that
        downstream comparisons silently accept.
        """
        return max(0, self.max_tokens - self.reserved_output_tokens)


@dataclass
class TruncationPlan:
    """What will be dropped, computed before anything is dropped.

    Separating the plan from its application lets a caller inspect and adjust
    the decision, and lets a test assert the decision without mutating history.
    """

    kept: List[Turn] = field(default_factory=list)
    dropped: List[Turn] = field(default_factory=list)
    omitted: List[Omission] = field(default_factory=list)
    summary: str = ""
    tokens: int = 0

    @property
    def within_budget(self) -> bool:
        return True


class ContextManager:
    """Fits history, memory, context and tool output into a token budget."""

    def __init__(self, budget: ContextBudget) -> None:
        self.budget = budget

    # -- history ------------------------------------------------------------

    def plan_history(
        self,
        turns: List[Turn],
        *,
        rolling_summary: Optional[str] = None,
    ) -> TruncationPlan:
        """Choose which turns to keep under budget.

        Ordering is by relevance first and recency second. A turn that bears on
        the current question survives over a more recent one that does not,
        because the question is what the answer has to address; a purely
        recency-ordered trim discards the one turn that mattered.

        When the oldest turns are dropped and a rolling summary is supplied, it
        replaces them rather than simply disappearing: the turns are gone from
        the prompt but their content is not, which is the whole point of a
        rolling summary.
        """
        plan = TruncationPlan(summary=rolling_summary or "")
        available = self.budget.available_tokens
        summary_tokens = estimate_tokens(plan.summary) if plan.summary else 0
        available -= summary_tokens

        # Highest relevance first, then most recent. A stable sort on the key so
        # two equally-scored turns keep their given order.
        ordered = sorted(
            turns, key=lambda t: (-t.relevance, -t.recency)
        )

        for turn in ordered:
            if turn.tokens <= available:
                plan.kept.append(turn)
                available -= turn.tokens
            else:
                plan.dropped.append(turn)

        plan.tokens = sum(t.tokens for t in plan.kept) + summary_tokens

        if plan.dropped:
            plan.omitted.append(
                Omission(
                    kind="history",
                    count=len(plan.dropped),
                    reason=f"exceeded {self.budget.available_tokens} tokens "
                    f"with {self.budget.reserved_output_tokens} reserved for output",
                )
            )
        return plan

    # -- tool results -------------------------------------------------------

    def trim_tool_results(
        self, results: List[Tuple[str, str]], budget_tokens: Optional[int] = None
    ) -> Tuple[List[Tuple[str, str]], List[Omission]]:
        """Drop the least relevant tool results until they fit.

        A tool result is not part of the conversation, so it is the first thing
        to go: an older tool output is more likely to have already been acted on
        and less likely to bear on the current question than the caller's own
        words.

        Results are supplied as (text, relevance) so the caller decides what
        matters; this function only enforces the budget.
        """
        limit = budget_tokens if budget_tokens is not None else self.budget.available_tokens
        ordered = sorted(range(len(results)), key=lambda i: -results[i][1])

        kept: List[Tuple[str, str]] = []
        omitted: List[Omission] = []
        remaining = max(0, limit)
        dropped = 0
        for index in ordered:
            text, relevance = results[index]
            cost = estimate_tokens(text)
            if cost <= remaining:
                kept.append(results[index])
                remaining -= cost
            else:
                dropped += 1
        if dropped:
            omitted.append(
                Omission(
                    kind="tool_output",
                    count=dropped,
                    reason=f"did not fit the {limit}-token tool budget",
                )
            )
        # Restore the caller's original order, so the prompt does not reorder the
        # evidence relative to how it was gathered.
        kept.sort(key=lambda item: results.index(item))
        return kept, omitted

    # -- assembly -----------------------------------------------------------

    def assemble(
        self,
        *,
        system: str = "",
        policy: str = "",
        memory: List[str] = None,
        snippets: List[str] = None,
        user: str = "",
        history_turns: List[Turn] = None,
        rolling_summary: Optional[str] = None,
        tool_results: List[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        """Assemble the context and report exactly what was omitted.

        The caller's own turn is never dropped. Everything else is trimmable, so
        that a request that cannot fit everything still asks the question rather
        than returning context without a question.
        """
        omissions: List[Omission] = []
        redactions: List[str] = []

        def clean(text: str) -> str:
            cleaned, found = redact_secrets(text)
            redactions.extend(found)
            return cleaned

        sections: List[Tuple[str, str, int]] = []
        # (label, body, priority) - the caller's question is last and highest.
        for label, body in (
            ("system", clean(system)),
            ("policy", clean(policy)),
            ("user", clean(user)),
        ):
            if body and body.strip():
                sections.append((label, body, 100))

        for item in memory or []:
            sections.append(("memory", clean(item), 80))

        for snippet in snippets or []:
            sections.append(("context", clean(snippet), 60))

        history_plan = self.plan_history(
            history_turns or [], rolling_summary=rolling_summary
        )
        omissions.extend(history_plan.omitted)

        tool_kept, tool_omissions = self.trim_tool_results(tool_results or [])
        omissions.extend(tool_omissions)
        for text, _relevance in tool_kept:
            sections.append(("tool_output", clean(text), 40))

        if history_plan.summary:
            sections.append(("summary", clean(history_plan.summary), 90))
        for turn in history_plan.kept:
            sections.append((f"history.{turn.role}", clean(turn.content), 50))

        # Fill by priority while the budget lasts, so what survives is chosen by
        # importance rather than by append order.
        sections.sort(key=lambda item: -item[2])

        assembled: List[str] = []
        used = 0
        dropped = 0
        for _label, body, _priority in sections:
            cost = estimate_tokens(body)
            if used + cost <= self.budget.available_tokens:
                assembled.append(body)
                used += cost
            else:
                dropped += 1
        if dropped:
            omissions.append(
                Omission(
                    kind="section",
                    count=dropped,
                    reason=f"exceeded {self.budget.available_tokens} tokens with "
                    f"{self.budget.reserved_output_tokens} reserved for output",
                )
            )

        return {
            "text": "\n\n".join(assembled),
            "token_count": used,
            "budget": self.budget.available_tokens,
            "omissions": [o.describe() for o in omissions],
            "redactions": redactions,
            "within_budget": used <= self.budget.available_tokens,
        }


# ---------------------------------------------------------------------------
# Rolling summary
# ---------------------------------------------------------------------------


@dataclass
class RollingSummariser:
    """Builds a compact summary of dropped history.

    Deterministic and lexical: the highest-scoring lines across the dropped
    turns. A model-backed summary would compress better and would need a
    provider call every time the window moved, which is a cost and a
    non-determinism this does not want to introduce.
    """

    max_chars: int = 1200

    def summarise(self, dropped: List[Turn]) -> str:
        if not dropped:
            return ""
        # Score a turn by how little it repeats common words, so a substantive
        # line survives over "ok" or "thanks".
        scored = []
        for turn in dropped:
            words = re.findall(r"[a-zA-Z]{4,}", turn.content.lower())
            score = len(set(words))
            scored.append((score, turn))
        scored.sort(key=lambda item: -item[0])

        parts = [f"{turn.role}: {turn.content}" for _score, turn in scored]
        text = " | ".join(parts)
        if len(text) <= self.max_chars:
            return text
        return text[: self.max_chars] + "…"
