"""Phase 59 - Documentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class APIDoc:
    endpoint: str
    method: str = "GET"
    description: str = ""
    parameters: list[str] = field(default_factory=list)
    responses: dict[str, str] = field(default_factory=dict)


@dataclass
class Tutorial:
    title: str
    content: str = ""
    difficulty: str = "beginner"


@dataclass
class Example:
    name: str
    code: str = ""
    description: str = ""


@dataclass
class ArchitectureDoc:
    title: str
    diagram: str = ""
    description: str = ""


@dataclass
class ContributionGuide:
    title: str
    content: str = ""


class Documentation:
    def __init__(self) -> None:
        self.api_docs: dict[str, APIDoc] = {}
        self.tutorials: dict[str, Tutorial] = {}
        self.examples: dict[str, Example] = {}
        self.architecture_docs: dict[str, ArchitectureDoc] = {}
        self.contribution_guides: dict[str, ContributionGuide] = {}

    def add_api_doc(self, doc: APIDoc) -> None:
        self.api_docs[doc.endpoint] = doc

    def add_tutorial(self, tutorial: Tutorial) -> None:
        self.tutorials[tutorial.title] = tutorial

    def add_example(self, example: Example) -> None:
        self.examples[example.name] = example

    def add_architecture_doc(self, doc: ArchitectureDoc) -> None:
        self.architecture_docs[doc.title] = doc

    def add_contribution_guide(self, guide: ContributionGuide) -> None:
        self.contribution_guides[guide.title] = guide

    def list_api_docs(self) -> list[str]:
        return list(self.api_docs.keys())

    def list_tutorials(self) -> list[str]:
        return list(self.tutorials.keys())

    def list_examples(self) -> list[str]:
        return list(self.examples.keys())

    def list_architecture_docs(self) -> list[str]:
        return list(self.architecture_docs.keys())

    def list_contribution_guides(self) -> list[str]:
        return list(self.contribution_guides.keys())
