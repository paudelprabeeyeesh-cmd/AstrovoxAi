from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.research.validation import AblationConfig, ValidationFramework
from models.llm.research.rollback import RollbackPlanManager, ChangeRecord, ImpactAnalysis, RollbackProcedure
from models.llm.research.reports import TechnicalReportGenerator, ExperimentDocumentation, ExperimentDocumenter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)


def build_ablation_configs(names: Optional[List[str]]) -> List[AblationConfig]:
    if names:
        return [AblationConfig(name=name) for name in names]
    return [
        AblationConfig("full"),
        AblationConfig("no_ffn", use_feedforward=False),
        AblationConfig("no_attn", use_attention=False),
        AblationConfig("no_norm", use_norm=False),
        AblationConfig("shallow", num_layers=1),
    ]


def build_rollback_plan(plan_id: str, experiment_id: str, baseline_commit: str) -> RollbackPlanManager:
    manager = RollbackPlanManager(plan_id=plan_id, experiment_id=experiment_id, baseline_commit=baseline_commit)
    manager.add_change(ChangeRecord(change_id="chg-001", author="validation", description="research validation framework", timestamp="2026-09-28T00:00:00Z", diff_hash="abc123", files_modified=["models/llm/research/validation.py"], impact_level="low"))
    manager.add_impact_analysis(ImpactAnalysis(component="research", impact_level="low", risk_score=0.1, affected_tests=["tests/test_research_validation.py"], affected_components=["models.llm.research"], rollback_difficulty="easy"))
    manager.add_procedure(RollbackProcedure(procedure_id="proc-001", name="revert research files", steps=["git checkout -- models/llm/research/", "pytest tests/test_research_validation.py"], estimated_time_minutes=5, prerequisites=[], success_criteria=["tests pass", "no import errors"]))
    return manager


def main() -> int:
    parser = argparse.ArgumentParser(description="Run research validation suite")
    parser.add_argument("--experiment-id", required=True, help="Experiment identifier")
    parser.add_argument("--ablation", nargs="*", help="Ablation config names to run")
    parser.add_argument("--rollback-plan", default="rp-001", help="Rollback plan identifier")
    parser.add_argument("--baseline-commit", default="HEAD~1", help="Baseline commit for rollback")
    parser.add_argument("--output-dir", default="validation_reports", help="Output directory for reports")
    parser.add_argument("--compare-baseline", action="store_true", help="Compare validation results with baseline")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    logger.info("Starting validation for experiment %s", args.experiment_id)

    validation_framework = ValidationFramework(experiment_id=args.experiment_id)
    validation_framework.set_rollback_plan(plan_id=args.rollback_plan)
    ablation_configs = build_ablation_configs(names=args.ablation)
    report = validation_framework.validate(ablation_configs=ablation_configs)
    report_path = os.path.join(args.output_dir, f"{args.experiment_id}_validation.json")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(validation_framework.report(), indent=2))
    logger.info("Validation report written to %s", report_path)

    rollback_manager = build_rollback_plan(plan_id=args.rollback_plan, experiment_id=args.experiment_id, baseline_commit=args.baseline_commit)
    rollback_manager.activate()
    rollback_dict = rollback_manager.to_dict()
    rollback_path = os.path.join(args.output_dir, f"{args.experiment_id}_rollback.json")
    with open(rollback_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(rollback_dict, indent=2))
    logger.info("Rollback plan written to %s", rollback_path)

    report_generator = TechnicalReportGenerator(experiment_id=args.experiment_id, title=f"Research Validation Report - {args.experiment_id}")
    report_generator.add_section("Validation Report", validation_framework.report())
    report_generator.add_section("Rollback Plan", rollback_dict)
    report_generator.set_metadata("experiment_id", args.experiment_id)
    report_generator.set_metadata("generated_at", report.generated_at)
    md_path = os.path.join(args.output_dir, f"{args.experiment_id}_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_generator.to_markdown())
    logger.info("Markdown report written to %s", md_path)

    doc = ExperimentDocumentation(experiment_id=args.experiment_id, title="Research Validation Framework", description="Phase validation framework for AstrovoxAi", hypothesis="Validation framework improves research reliability", methodology="Benchmark, ablation, reproducibility, and rollback", parameters={"experiment_id": args.experiment_id}, artifacts=[report_path, rollback_path, md_path], dependencies={"pytest": ">=8.0", "torch": ">=2.0"}, tags=["research", "validation", "phase"])
    documenter = ExperimentDocumenter()
    documenter.add_documentation(doc)
    docs_path = os.path.join(args.output_dir, f"{args.experiment_id}_docs.json")
    documenter.publish(docs_path)
    logger.info("Experiment documentation written to %s", docs_path)

    if args.compare_baseline:
        logger.info("Comparing with baseline")
        baseline_path = os.path.join(args.output_dir, f"{args.experiment_id}_baseline.json")
        baseline = {"benchmarks": {}, "latency": {}, "memory": {}}
        if os.path.exists(baseline_path):
            with open(baseline_path, "r", encoding="utf-8") as f:
                baseline = json.load(f)
        current = validation_framework.report()
        comparison = {
            "current": current,
            "baseline": baseline,
            "improvements": {},
        }
        comp_path = os.path.join(args.output_dir, f"{args.experiment_id}_comparison.json")
        with open(comp_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(comparison, indent=2))
        logger.info("Comparison written to %s", comp_path)

    logger.info("Validation suite completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
