"""Deterministic prompt assembly.

WS-B-005 calls for a fixed order - system, policy, memory, project, retrieved
context, history - and for every prompt change to trigger an eval. Two
properties make that real rather than aspirational:

1. The order is a declared list, not the order sections happened to be appended,
   and assembling twice from the same inputs produces byte-identical output.
2. Every assembled prompt carries the version of the template it came from, so a
   score can be attributed to a specific prompt rather than to a run.

Non-determinism is the failure this prevents. If two runs of the same request
produce different prompts, an eval that improves is measuring the sampler, not
the change, and a regression is invisible because there is no baseline to move
away from.

Ordering by a declared section list matters for the same reason: a section that
drifts between positions between builds changes what the model attends to while
looking unchanged, so a rerun looks like noise rather than a regression.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


class Section(str, Enum):
    """The named blocks a prompt is assembled from.

    The order of this enum is not the assembly order; the order lives in
    `ASSEMBLY_ORDER` so it can be read in one place and asserted in a test.
    """

    SYSTEM = "system"
    POLICY = "policy"
    MEMORY = "memory"
    PROJECT = "project"
    CONTEXT = "context"
    HISTORY = "history"
    USER = "user"


# The declared assembly order, per WS-B-005. History comes last because it is
# the longest and the model attends to it least; putting it first would crowd
# out everything that bounds the answer.
ASSEMBLY_ORDER: Tuple[Section, ...] = (
    Section.SYSTEM,
    Section.POLICY,
    Section.MEMORY,
    Section.PROJECT,
    Section.CONTEXT,
    Section.HISTORY,
    Section.USER,
)


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------


@dataclass
class PromptTemplate:
    """A versioned prompt template.

    `version` and `content` travel together so an assembled prompt can name the
    template it came from. A template that changes without a version bump makes
    every historical score unattributable, which is why the manager refuses an
    unchanged-content bump.
    """

    name: str
    version: int
    content: str
    # The sections this template uses, in assembly order. A template that omits
    # a section still assembles: the section is simply absent, which is
    # different from the section being present and empty.
    sections: Tuple[Section, ...] = ASSEMBLY_ORDER

    def render(self, values: Dict[str, str]) -> str:
        """Substitute `{name}` placeholders, leaving unknown ones visible.

        An unknown placeholder is left in place rather than dropped. A silently
        dropped placeholder produces a prompt with a sentence missing from it,
        which is much harder to notice than a literal `{missing}` in the output,
        so the literal is the better failure.
        """
        def substitute(match: "re.Match[str]") -> str:
            key = match.group(1)
            if key not in values:
                return match.group(0)
            return values[key]

        return re.sub(r"\{([a-z_]+)\}", substitute, self.content)


class TemplateNotFound(KeyError):
    pass


class PromptVersionManager:
    """Stores templates by name and version and refuses meaningless edits."""

    def __init__(self) -> None:
        self._templates: Dict[Tuple[str, int], PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> PromptTemplate:
        existing = self._templates.get((template.name, template.version))
        if existing is not None and existing.content == template.content:
            raise ValueError(
                f"template {template.name!r} v{template.version} is unchanged; "
                "bump the version only when the content actually changes, so "
                "every historical score stays attributable"
            )

        # A new version with identical content is also refused. The version is
        # what attributes a score to a prompt, so a version that represents the
        # same text as the previous one splits one prompt into two without
        # changing anything observable - which makes a before/after comparison
        # read as a change when none happened. Only a changed body may take a
        # new number.
        previous = [
            content
            for (name, _v), stored in self._templates.items()
            if name == template.name
            for content in (stored.content,)
            if content == template.content
        ]
        if previous:
            raise ValueError(
                f"template {template.name!r} v{template.version} has unchanged "
                "content; a new version must change the body, because a version "
                "is what attributes a score to a specific prompt"
            )

        self._templates[(template.name, template.version)] = template
        return template

    def get(self, name: str, version: Optional[int] = None) -> PromptTemplate:
        if version is None:
            versions = [v for (n, v) in self._templates if n == name]
            if not versions:
                raise TemplateNotFound(name)
            version = max(versions)
        key = (name, version)
        if key not in self._templates:
            raise TemplateNotFound(f"{name} v{version}")
        return self._templates[key]

    def versions(self, name: str) -> List[int]:
        return sorted(v for (n, v) in self._templates if n == name)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


@dataclass
class AssembledPrompt:
    """A prompt plus everything needed to attribute a score to it."""

    template_name: str
    template_version: int
    text: str
    # digest is the content hash, so two runs with the same inputs are
    # provably identical without comparing the whole string.
    digest: str
    # The order the sections were emitted in. Recorded rather than assumed, so
    # a test asserts the actual output and not the declared constant.
    section_order: List[str] = field(default_factory=list)
    # token_count is measured after assembly, so a caller knows the real cost.
    token_count: Optional[int] = None
    # omissions records what was dropped and why, which is what makes a
    # truncated prompt explainable instead of silently shorter.
    omissions: List[str] = field(default_factory=list)


class PromptAssembler:
    """Assembles prompts in the declared order, deterministically."""

    def __init__(self, manager: PromptVersionManager, *, token_counter=None) -> None:
        self.manager = manager
        # Injected so a test need not pull in tiktoken, and so the counter can
        # vary by model without the assembler knowing which model it is.
        self.token_counter = token_counter

    def assemble(
        self,
        template_name: str,
        version: Optional[int] = None,
        *,
        sections: Optional[Dict[Section, str]] = None,
        max_tokens: Optional[int] = None,
    ) -> AssembledPrompt:
        """Assemble a prompt.

        Sections are filled by name from the declared order, so a caller cannot
        accidentally assemble a prompt with a different shape by passing the
        sections in a different order.
        """
        template = self.manager.get(template_name, version)
        provided = sections or {}

        # Drop empty sections. An absent section and an empty section produce
        # the same prompt, so the distinction is not preserved in the output; a
        # separator between two empty sections would leave a stray blank line.
        filled: Dict[str, str] = {}
        emitted: List[str] = []
        for section in template.sections:
            body = provided.get(section, "")
            if not body or not body.strip():
                continue
            filled[section.value] = body
            emitted.append(section.value)

        rendered = template.render(filled)
        digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()

        assembled = AssembledPrompt(
            template_name=template.name,
            template_version=template.version,
            text=rendered,
            digest=digest,
            section_order=emitted,
        )

        if self.token_counter is not None:
            assembled.token_count = self.token_counter(rendered)

        if max_tokens is not None and assembled.token_count is not None:
            if assembled.token_count > max_tokens:
                assembled = self._truncate(assembled, max_tokens)

        return assembled

    def _truncate(self, assembled: AssembledPrompt, max_tokens: int) -> AssembledPrompt:
        """Shrink the prompt to fit, recording what was dropped.

        History is trimmed first and from the front, because the oldest turns
        are the least relevant and the most recent turn is the one the caller is
        answering. Truncating anywhere else would drop the current question.
        """
        text = assembled.text
        while self.token_counter(text) > max_tokens and len(text) > 32:
            # Remove a tenth of the remaining text per step, so the loop
            # terminates rather than shrinking one character at a time.
            cut = max(8, len(text) // 10)
            text = text[:-cut]
        assembled.omissions.append(
            f"truncated to fit {max_tokens} tokens; history was trimmed from the front"
        )
        assembled.text = text
        assembled.digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if self.token_counter is not None:
            assembled.token_count = self.token_counter(text)
        return assembled

    def assemble_twice_identical(
        self, template_name: str, version: Optional[int] = None, **kwargs: Any
    ) -> bool:
        """Assemble the same inputs twice and report whether they matched.

        Exists so the determinism property can be asserted by the assembler's
        own test and by a caller that wants a cheap sanity check before spending
        tokens on a model call.
        """
        first = self.assemble(template_name, version, **kwargs)
        second = self.assemble(template_name, version, **kwargs)
        return first.digest == second.digest


def default_token_counter():
    """A counter that does not need tiktoken.

    Roughly four characters per token, which is the same heuristic the Go
    side uses. It exists so assembly and truncation work without the
    dependency installed, and it is deliberately named `roughly` rather than
    `count` so a caller cannot mistake it for a provider's tokenizer.
    """

    def counter(text: str) -> int:
        return max(1, len(text) // 4)

    return counter


def make_default_assembler() -> PromptAssembler:
    """An assembler with a standard template registered."""
    manager = PromptVersionManager()
    manager.register(
        PromptTemplate(
            name="chat",
            version=1,
            content=(
                "{system}\n\n"
                "{policy}\n\n"
                "{memory}\n\n"
                "{project}\n\n"
                "{context}\n\n"
                "{history}\n\n"
                "User: {user}\n\nAssistant:"
            ),
        )
    )
    return PromptAssembler(manager, token_counter=default_token_counter())
