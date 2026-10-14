"""Tests for deterministic prompt assembly.

Two properties are being pinned, and both are the ones that make evals
meaningful rather than decorative:

1. Same inputs produce byte-identical output. Without this, an eval that
   "improves" may be measuring the sampler, not the change, and a regression is
   invisible because there is no baseline to move away from.
2. Sections emit in the declared order, whatever order the caller passed them.
   A section drifting between positions changes what the model attends to while
   looking unchanged, so a rerun reads as noise instead of a regression.

The rest are the guard rails: an unknown placeholder stays visible rather than
silently dropping a sentence, and truncation records what it dropped.
"""

import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
sys.path.insert(0, ".")

import pytest

from app.prompt_assembly import (
    ASSEMBLY_ORDER,
    PromptAssembler,
    PromptTemplate,
    PromptVersionManager,
    Section,
    TemplateNotFound,
    default_token_counter,
    make_default_assembler,
)
from app.prompt_assembly import AssembledPrompt


@pytest.fixture
def assembler():
    return make_default_assembler()


FULL_SECTIONS = {
    Section.SYSTEM: "You are Astrovox.",
    Section.POLICY: "Never disclose credentials.",
    Section.MEMORY: "User prefers dark mode.",
    Section.PROJECT: "Project: Atlas.",
    Section.CONTEXT: "[doc-1] Credential rotation requires a new password.",
    Section.HISTORY: "User: hello\nAssistant: hi",
    Section.USER: "How do I rotate credentials?",
}


def test_assembly_is_deterministic(assembler):
    first = assembler.assemble("chat", 1, sections=FULL_SECTIONS)
    second = assembler.assemble("chat", 1, sections=FULL_SECTIONS)
    assert first.digest == second.digest
    assert first.text == second.text


def test_section_order_is_declared_not_supplied(assembler):
    # The caller passes a dict, whose order must not matter.
    reversed_order = {}
    for section in reversed(list(ASSEMBLY_ORDER)):
        reversed_order[section] = FULL_SECTIONS[section]

    natural = assembler.assemble("chat", 1, sections=FULL_SECTIONS)
    reversed_result = assembler.assemble("chat", 1, sections=reversed_order)
    assert natural.digest == reversed_result.digest
    assert natural.section_order == list(s.value for s in ASSEMBLY_ORDER)


def test_empty_sections_are_omitted_without_leaving_gaps(assembler):
    partial = {
        Section.SYSTEM: "You are Astrovox.",
        Section.USER: "How do I rotate credentials?",
    }
    result = assembler.assemble("chat", 1, sections=partial)
    assert result.section_order == ["system", "user"]
    # An empty section must not leave a blank line where it would have been,
    # which would make the prompt differ from one where it was never supplied.
    assert "\n\n\n\n" not in result.text


def test_a_whitespace_only_section_is_treated_as_empty(assembler):
    result = assembler.assemble(
        "chat",
        1,
        sections={Section.SYSTEM: "   \n  ", Section.USER: "hi"},
    )
    assert result.section_order == ["user"]


def test_an_unknown_placeholder_stays_visible(assembler):
    manager = PromptVersionManager()
    manager.register(
        PromptTemplate(name="t", version=1, content="{known} and {missing}")
    )
    a = PromptAssembler(manager, token_counter=default_token_counter())
    result = a.assemble("t", 1, sections={})
    result = a.assemble("t", 1, sections={Section.SYSTEM: "known-body"})
    # The literal remains rather than being replaced with an empty string,
    # because a missing sentence is far harder to notice than a visible marker.
    assert "{missing}" in result.text


def test_template_version_is_recorded(assembler):
    result = assembler.assemble("chat", 1, sections=FULL_SECTIONS)
    assert result.template_name == "chat"
    assert result.template_version == 1


def test_a_unchanged_re_register_is_refused():
    manager = PromptVersionManager()
    template = PromptTemplate(name="t", version=1, content="body")
    manager.register(template)
    with pytest.raises(ValueError):
        # Bumping nothing makes every historical score unattributable, which is
        # why the manager refuses rather than accepting a no-op version.
        manager.register(PromptTemplate(name="t", version=2, content="body"))


def test_a_changed_template_registers_at_a_new_version():
    manager = PromptVersionManager()
    manager.register(PromptTemplate(name="t", version=1, content="body"))
    manager.register(PromptTemplate(name="t", version=2, content="new body"))
    assert manager.versions("t") == [1, 2]
    assert manager.get("t", 1).content == "body"
    assert manager.get("t", 2).content == "new body"


def test_get_without_a_version_returns_the_latest():
    manager = PromptVersionManager()
    manager.register(PromptTemplate(name="t", version=1, content="a"))
    manager.register(PromptTemplate(name="t", version=7, content="b"))
    assert manager.get("t").version == 7


def test_an_unknown_template_raises():
    with pytest.raises(TemplateNotFound):
        make_default_assembler().assemble("nope", 1)


def test_an_unknown_version_raises():
    with pytest.raises(TemplateNotFound):
        make_default_assembler().assemble("chat", 99)


def test_token_count_is_measured(assembler):
    result = assembler.assemble("chat", 1, sections=FULL_SECTIONS)
    assert result.token_count is not None
    assert result.token_count > 0


def test_a_custom_counter_is_used(assembler):
    seen = []

    def counter(text):
        seen.append(len(text))
        return 1

    assembler.token_counter = counter
    result = assembler.assemble("chat", 1, sections=FULL_SECTIONS)
    assert seen != []
    assert result.token_count == 1


def test_truncation_records_what_it_dropped(assembler):
    # A prompt far over the cap must be shrunk, and the omission must be
    # recorded rather than the prompt silently becoming shorter.
    huge = {
        Section.SYSTEM: "word " * 5000,
        Section.USER: "question",
    }
    result = assembler.assemble("chat", 1, sections=huge, max_tokens=50)
    assert result.token_count <= 50
    assert result.omissions, "truncation left no record"


def test_truncation_recomputes_the_digest(assembler):
    huge = {Section.SYSTEM: "word " * 5000, Section.USER: "question"}
    result = assembler.assemble("chat", 1, sections=huge, max_tokens=50)
    import hashlib

    assert result.digest == hashlib.sha256(
        result.text.encode("utf-8")
    ).hexdigest()


def test_no_truncation_without_a_cap(assembler):
    result = assembler.assemble("chat", 1, sections=FULL_SECTIONS)
    assert result.omissions == []


def test_no_truncation_when_the_counter_is_absent():
    manager = PromptVersionManager()
    manager.register(PromptTemplate(name="t", version=1, content="{system}"))
    a = PromptAssembler(manager)
    result = a.assemble(
        "t", 1, sections={Section.SYSTEM: "x" * 5000}, max_tokens=10
    )
    # Without a counter the cap cannot be evaluated, so nothing is trimmed and
    # nothing is claimed to have been trimmed.
    assert result.omissions == []
    assert len(result.text) == 5000


def test_assemble_twice_identical_reports_true(assembler):
    assert assembler.assemble_twice_identical("chat", 1, sections=FULL_SECTIONS)


def test_assembly_order_matches_the_spec():
    # WS-B-005 declares the order explicitly, so pin it rather than trusting it
    # has not been reordered by an edit.
    assert [s.value for s in ASSEMBLY_ORDER] == [
        "system",
        "policy",
        "memory",
        "project",
        "context",
        "history",
        "user",
    ]


def test_the_history_is_last_before_the_user_turn(assembler):
    # The current question must outrank the history in position; putting the
    # history first crowds out the thing the caller is actually asking.
    result = assembler.assemble("chat", 1, sections=FULL_SECTIONS)
    assert result.section_order[-2:] == ["history", "user"]


def test_a_section_order_is_the_template_order_not_assembly_order():
    # A template that declares a subset must emit in that subset's order.
    manager = PromptVersionManager()
    manager.register(
        PromptTemplate(
            name="t",
            version=1,
            content="{user} {system}",
            sections=(Section.USER, Section.SYSTEM),
        )
    )
    a = PromptAssembler(manager, token_counter=default_token_counter())
    result = a.assemble(
        "t", 1, sections={Section.USER: "q", Section.SYSTEM: "s"}
    )
    assert result.section_order == ["user", "system"]


def test_default_token_counter_is_positive_for_empty_text():
    assert default_token_counter()("") == 1
