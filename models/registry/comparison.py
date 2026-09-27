import json
from typing import Any, Dict, List

from .registry import compare_models
from .cards import generate_model_card, save_model_card


def compare_and_report(name: str, versions: List[str]) -> Dict[str, Any]:
    comparison = compare_models(name, versions)
    report = {
        "model": name,
        "versions_compared": versions,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "comparison": {},
    }

    for v, data in comparison.items():
        report["comparison"][v] = {
            "sha256": data.get("sha256"),
            "status": data.get("status"),
            "size_bytes": data.get("size_bytes"),
            "registered_at": data.get("registered_at"),
            "evaluation": data.get("evaluation", {}),
            "metadata": data.get("metadata", {}),
        }

    report_path = (
        __import__("pathlib").Path(__file__).resolve().parent.parent.parent
        / "models"
        / "registry"
        / "comparisons"
        / f"{name}_comparison.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str))
    return report


def generate_comparison_card(name: str, versions: List[str]) -> str:
    comparison = compare_models(name, versions)
    lines = [f"# Model Comparison: {name}\n", f"**Versions:** {', '.join(versions)}\n"]
    lines.append("| Version | SHA256 | Status | Size (bytes) | Evaluation |\n")
    lines.append("|---------|--------|--------|--------------|------------|\n")
    for v, data in comparison.items():
        eval_summary = json.dumps(data.get("evaluation", {}), default=str)
        lines.append(
            f"| {v} | {data.get('sha256', 'N/A')} | {data.get('status', 'N/A')} | "
            f"{data.get('size_bytes', 'N/A')} | {eval_summary[:50]} |\n"
        )
    return "".join(lines)
