"""Model card generation.

A model card is what makes a repository usable by someone who was not there
when it was trained. This renders YAML front matter, which is what the Hub
reads to populate a model page, followed by sections covering architecture,
training data, evaluation, and intended use.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

DEFAULT_LICENSE = "apache-2.0"
DEFAULT_LIBRARY = "astrovox"


@dataclass
class ModelInfo:
    """What a card needs to know about a model."""

    model_id: str
    description: str = ""
    architecture: str = ""
    parameter_count: int = 0
    dataset: str = ""
    dataset_size: int = 0
    framework_version: str = ""
    library: str = DEFAULT_LIBRARY
    license: str = DEFAULT_LICENSE
    language: str = "en"
    task: str = "text-generation"
    base_model: str = ""
    training_steps: int = 0
    final_loss: float | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    hardware: str = ""
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    tags: Sequence[str] = ()
    limitations: Sequence[str] = ()
    intended_use: str = ""
    base_model_card_data: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the info as a plain dictionary."""
        return {k: v for k, v in self.__dict__.items() if v not in (None, "", [], {})}

    @classmethod
    def from_bundle(
        cls,
        model_id: str,
        bundle: Any,
        repo_id: str = "",
        **overrides: Any,
    ) -> "ModelInfo":
        """Build a :class:`ModelInfo` from a discovered checkpoint bundle."""
        manifest = dict(getattr(bundle, "manifest", {}) or {})
        config = dict(getattr(bundle, "config", {}) or {})

        tags = [
            "astrovox",
            str(config.get("model_type", "transformer")),
            str(config.get("task", "text-generation")),
            "pytorch-like",
        ]
        tags.extend(str(t) for t in config.get("tags", []) if t)

        info = cls(
            model_id=model_id,
            architecture=str(config.get("architectures", [config.get("model_type", "")])[0]
                             if config.get("architectures") else ""),
            parameter_count=int(manifest.get("parameter_count", 0) or config.get("parameter_count", 0) or 0),
            dataset=str(manifest.get("dataset", config.get("dataset", "")) or ""),
            dataset_size=int(manifest.get("dataset_size", 0) or 0),
            framework_version=str(manifest.get("version", "") or _framework_version()),
            license=str(config.get("license", DEFAULT_LICENSE)),
            language=str(config.get("language", "en")),
            task=str(config.get("task", "text-generation")),
            base_model=str(config.get("base_model", "")),
            training_steps=int(manifest.get("step", manifest.get("steps", 0)) or 0),
            final_loss=manifest.get("final_loss"),
            metrics={k: v for k, v in manifest.items() if isinstance(v, (int, float))},
            tags=tuple(dict.fromkeys(tags)),
            hyperparameters=dict(manifest.get("hyperparameters", {}) or {}),
        )
        for key, value in overrides.items():
            if value is not None:
                setattr(info, key, value)
        return info


def _framework_version() -> str:
    """Return this package's version, or an empty string if unavailable."""
    try:
        from astrovox import __version__

        return str(__version__)
    except Exception:  # pragma: no cover - defensive
        return ""


def _yaml_scalar(value: Any) -> str:
    """Render a value as YAML, quoting where necessary."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(ch in text for ch in ":#{}[]&*!|>'\"%@`,") or text.strip() != text:
        return json.dumps(text)
    return text


def _render_yaml(data: dict[str, Any], indent: int = 0) -> str:
    """Render a flat mapping as YAML front matter."""
    lines = []
    pad = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(_render_yaml(value, indent + 1))
        elif isinstance(value, (list, tuple)):
            if not value:
                lines.append(f"{pad}{key}: []")
            else:
                lines.append(f"{pad}{key}:")
                lines.extend(f"{pad}  - {_yaml_scalar(item)}" for item in value)
        else:
            lines.append(f"{pad}{key}: {_yaml_scalar(value)}")
    return "\n".join(line for line in lines if line)


def _human_count(value: int) -> str:
    """Render a parameter count in a readable form."""
    if value >= 1_000_000_000:
        return f"{value / 1e9:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1e6:.2f}M"
    if value >= 1_000:
        return f"{value / 1e3:.1f}K"
    return str(value)


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Render a Markdown table, skipping it entirely when there are no rows."""
    if not rows:
        return ""
    body = ["| " + " | ".join(str(h) for h in headers) + " |",
            "|" + "|".join("---" for _ in headers) + "|"]
    body.extend("| " + " | ".join(str(c) for c in row) + " |" for row in rows)
    return "\n".join(body)


def build_card(info: ModelInfo, filename: str = "") -> str:
    """Render the full model card as Markdown with YAML front matter."""
    front_matter: dict[str, Any] = {
        "language": info.language,
        "license": info.license,
        "library_name": info.library,
        "tags": list(info.tags),
        "task": info.task,
    }
    if info.base_model:
        front_matter["base_model"] = info.base_model
    if info.architecture:
        front_matter["pipeline_tag"] = info.task
    if info.base_model_card_data:
        front_matter["base_model_card_data"] = info.base_model_card_data
    front_matter.update(info.extra)

    sections: list[str] = []
    header = f"# {info.model_id}"
    sections.append(header)

    if info.description:
        sections.append(info.description)
    else:
        sections.append(
            f"A {info.task} model trained with [Astrovox]"
            f"(https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi)."
        )

    if filename:
        sections.append(
            _table(
                ["File", "Purpose"],
                [
                    [f"`{filename}`", "Model weights"],
                    ["`astrovox_config.json`", "Architecture and hyperparameters"],
                    ["`model_card.json`", "This card as structured data"],
                ],
            )
        )

    facts: list[list[Any]] = []
    if info.architecture:
        facts.append(["Architecture", info.architecture])
    if info.parameter_count:
        facts.append(["Parameters", f"{info.parameter_count:,} ({_human_count(info.parameter_count)})"])
    if info.framework_version:
        facts.append(["Astrovox version", info.framework_version])
    if info.training_steps:
        facts.append(["Training steps", f"{info.training_steps:,}"])
    if info.hardware:
        facts.append(["Hardware", info.hardware])
    if info.final_loss is not None:
        facts.append(["Final loss", f"{info.final_loss:.4f}"])
    if facts:
        sections.append("## Model Details\n\n" + _table(["Property", "Value"], facts))

    training: list[list[Any]] = []
    if info.dataset:
        training.append(["Dataset", info.dataset])
    if info.dataset_size:
        training.append(["Dataset size", f"{info.dataset_size:,} samples"])
    if info.training_steps:
        training.append(["Steps", f"{info.training_steps:,}"])
    if info.hardware:
        training.append(["Hardware", info.hardware])
    if info.final_loss is not None:
        training.append(["Final loss", f"{info.final_loss:.4f}"])
    if info.hyperparameters:
        for key, value in info.hyperparameters.items():
            training.append([key.replace("_", " ").title(), value])
    if training:
        sections.append("## Training\n\n" + _table(["Item", "Value"], training))

    if info.metrics:
        rows = [[k, f"{v:.4f}"] for k, v in sorted(info.metrics.items())]
        sections.append("## Evaluation\n\n" + _table(["Metric", "Value"], rows))

    sections.append(
        "## Usage\n\n"
        "```python\n"
        "from astrovox import tensor\n"
        f"from astrovox.hub import pull_model\n\n"
        f'model = pull_model("{info.model_id}")\n'
        "output = model(tensor(token_ids))\n"
        "```"
    )

    sections.append(
        "## Intended Use\n\n"
        + (info.intended_use or
           "Intended for research and experimentation with small-scale language "
           "models. Not tuned for safety-critical or high-stakes deployment.")
    )

    limitations = list(info.limitations) or [
        f"Trained on a small corpus ({info.dataset or 'unspecified'}) and will not "
        "generalize beyond it.",
        "This is a research checkpoint, not a production model.",
    ]
    sections.append("## Limitations\n\n" + "\n".join(f"- {item}" for item in limitations))

    sections.append(
        "## License\n\n"
        f"This model is released under the {info.license} license."
    )

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sections.append(f"---\n\n*Card generated by Astrovox on {generated}.*")

    return "---\n" + _render_yaml(front_matter) + "\n---\n\n" + "\n\n".join(
        section for section in sections if section
    ) + "\n"


def write_card(
    path: str | Path, info: ModelInfo, filename: str = ""
) -> Path:
    """Write a model card to ``path`` and return the path."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_card(info, filename), encoding="utf-8")
    return target


def build_manifest(info: ModelInfo, filename: str = "") -> dict[str, Any]:
    """Return the machine-readable manifest stored beside a checkpoint."""
    return {
        "model_id": info.model_id,
        "filename": filename,
        "architecture": info.architecture,
        "parameter_count": info.parameter_count,
        "dataset": info.dataset,
        "dataset_size": info.dataset_size,
        "framework": "astrovox",
        "framework_version": info.framework_version,
        "license": info.license,
        "task": info.task,
        "language": info.language,
        "training_steps": info.training_steps,
        "final_loss": info.final_loss,
        "metrics": info.metrics,
        "hyperparameters": info.hyperparameters,
        "tags": list(info.tags),
    }