from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class ExperimentDocumentation:
    experiment_id: str
    title: str
    description: str
    hypothesis: str
    methodology: str
    parameters: Dict
    artifacts: List[str]
    dependencies: Dict
    tags: List[str]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class TechnicalReport:
    experiment_id: str
    title: str
    sections: Dict[str, Any]
    metadata: Dict[str, str]
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class TechnicalReportGenerator:
    def __init__(self, experiment_id: str, title: str):
        self.experiment_id = experiment_id
        self.title = title
        self.sections: Dict[str, Any] = {}
        self.metadata: Dict[str, str] = {}

    def add_section(self, name: str, content: Any) -> TechnicalReportGenerator:
        self.sections[name] = content
        return self

    def set_metadata(self, key: str, value: str) -> TechnicalReportGenerator:
        self.metadata[key] = value
        return self

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", f"Experiment: {self.experiment_id}", f"Generated: {datetime.utcnow().isoformat()}Z", ""]
        for section, content in self.sections.items():
            lines.append(f"## {section}")
            lines.append("")
            if isinstance(content, dict):
                for k, v in content.items():
                    lines.append(f"### {k}")
                    lines.append("")
                    if isinstance(v, list):
                        for item in v:
                            lines.append(f"- {item}")
                    else:
                        lines.append(str(v))
                    lines.append("")
            else:
                lines.append(str(content))
                lines.append("")
        return "\n".join(lines)

    def to_json(self) -> str:
        payload = {
            "experiment_id": self.experiment_id,
            "title": self.title,
            "sections": {k: (str(v) if not isinstance(v, (dict, list)) else v) for k, v in self.sections.items()},
            "metadata": self.metadata,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        return json.dumps(payload, indent=2)

    def to_pdf(self, output_path: str) -> str:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            elements: List[Any] = [Paragraph(self.title, styles["Title"]), Spacer(1, 12), Paragraph(f"Experiment: {self.experiment_id}", styles["Heading2"]), Spacer(1, 12)]
            for section, content in self.sections.items():
                elements.append(Paragraph(section, styles["Heading2"]))
                elements.append(Paragraph(str(content), styles["BodyText"]))
                elements.append(Spacer(1, 12))
            doc.build(elements)
            return output_path
        except ImportError:
            logger.warning("reportlab not installed, falling back to markdown")
            return ""


class ExperimentDocumenter:
    def __init__(self):
        self.documents: List[ExperimentDocumentation] = []

    def add_documentation(self, doc: ExperimentDocumentation) -> ExperimentDocumenter:
        self.documents.append(doc)
        logger.info("Documented experiment %s", doc.experiment_id)
        return self

    def get_documentation(self, experiment_id: str) -> Optional[ExperimentDocumentation]:
        for doc in self.documents:
            if doc.experiment_id == experiment_id:
                return doc
        return None

    def list_documented(self) -> List[str]:
        return [d.experiment_id for d in self.documents]

    def publish(self, output_path: str) -> str:
        payload = {
            "experiments": [
                {
                    "experiment_id": d.experiment_id,
                    "title": d.title,
                    "description": d.description,
                    "hypothesis": d.hypothesis,
                    "methodology": d.methodology,
                    "parameters": d.parameters,
                    "artifacts": d.artifacts,
                    "dependencies": d.dependencies,
                    "tags": d.tags,
                    "created_at": d.created_at,
                }
                for d in self.documents
            ],
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info("Published documentation for %d experiments", len(self.documents))
        return output_path
