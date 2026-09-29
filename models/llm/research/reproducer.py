"""Research paper reproduction and experiment validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PaperSection:
    title: str
    content: str


@dataclass
class ParsedPaper:
    title: str
    authors: list[str]
    sections: list[PaperSection]
    abstract: str = ""


@dataclass
class ExperimentSpec:
    name: str
    dataset: str
    model: str
    hyperparameters: dict[str, Any]
    metrics: list[str]


@dataclass
class ExperimentResult:
    experiment_name: str
    metrics: dict[str, float]
    reproduced: bool = True


@dataclass
class ComparisonResult:
    experiment: str
    paper_value: float
    reproduced_value: float
    difference: float
    relative_error: float
    within_tolerance: bool


class PaperParser:
    def parse(self, paper_text: str) -> ParsedPaper:
        title_match = re.search(r"Title[:\s]+(.+)", paper_text, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Untitled"
        authors_match = re.search(r"Authors?[:\s]+(.+)", paper_text, re.IGNORECASE)
        authors = [a.strip() for a in authors_match.group(1).split(",")] if authors_match else ["Unknown"]
        sections = []
        section_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        for match in section_pattern.finditer(paper_text):
            sections.append(PaperSection(title=match.group(1).strip(), content=paper_text[match.start() :]))
        if not sections:
            sections.append(PaperSection(title="Full Text", content=paper_text))
        abstract_match = re.search(r"Abstract[:\s]+(.+?)(?:\n\n|\Z)", paper_text, re.IGNORECASE | re.DOTALL)
        abstract = abstract_match.group(1).strip() if abstract_match else ""
        return ParsedPaper(title=title, authors=authors, sections=sections, abstract=abstract)

    def extract_experiments(self, parsed_paper: ParsedPaper) -> list[ExperimentSpec]:
        experiments = []
        for section in parsed_paper.sections:
            if "experiment" in section.title.lower() or "result" in section.title.lower():
                exp = ExperimentSpec(
                    name=section.title,
                    dataset=self._extract_dataset(section.content),
                    model=self._extract_model(section.content),
                    hyperparameters=self._extract_hyperparameters(section.content),
                    metrics=self._extract_metrics(section.content),
                )
                experiments.append(exp)
        return experiments if experiments else [
            ExperimentSpec(
                name="default",
                dataset="unknown",
                model="unknown",
                hyperparameters={},
                metrics=["accuracy"],
            )
        ]

    @staticmethod
    def _extract_dataset(text: str) -> str:
        m = re.search(r"dataset[:\s]+([A-Za-z0-9_]+)", text, re.IGNORECASE)
        return m.group(1) if m else "unknown"

    @staticmethod
    def _extract_model(text: str) -> str:
        m = re.search(r"model[:\s]+([A-Za-z0-9_\-]+)", text, re.IGNORECASE)
        return m.group(1) if m else "unknown"

    @staticmethod
    def _extract_hyperparameters(text: str) -> dict[str, Any]:
        params: dict[str, Any] = {}
        for m in re.finditer(r"(\w+)[:\s]+([\d\.]+)", text):
            try:
                params[m.group(1)] = float(m.group(2))
            except ValueError:
                pass
        return params

    @staticmethod
    def _extract_metrics(text: str) -> list[str]:
        metrics = []
        for m in re.finditer(r"(accuracy|precision|recall|f1|loss|bleu|rouge)", text, re.IGNORECASE):
            metric = m.group(1).lower()
            if metric not in metrics:
                metrics.append(metric)
        return metrics if metrics else ["accuracy"]


class ExperimentReproducer:
    def __init__(self):
        self._results: list[ExperimentResult] = []

    def reproduce(self, spec: ExperimentSpec, run_fn: Callable) -> ExperimentResult:
        metrics = run_fn(spec)
        result = ExperimentResult(experiment_name=spec.name, metrics=metrics, reproduced=True)
        self._results.append(result)
        return result

    def compare(self, result: ExperimentResult, paper_values: dict[str, float], tolerance: float = 0.05) -> list[ComparisonResult]:
        comparisons = []
        for metric, paper_value in paper_values.items():
            reproduced_value = result.metrics.get(metric, 0.0)
            diff = abs(reproduced_value - paper_value)
            rel_error = diff / abs(paper_value) if paper_value != 0 else float("inf")
            comparisons.append(
                ComparisonResult(
                    experiment=result.experiment_name,
                    paper_value=paper_value,
                    reproduced_value=reproduced_value,
                    difference=diff,
                    relative_error=rel_error,
                    within_tolerance=rel_error <= tolerance,
                )
            )
        return comparisons

    def all_results(self) -> list[ExperimentResult]:
        return list(self._results)
