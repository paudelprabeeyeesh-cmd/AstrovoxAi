#!/usr/bin/env python3
"""
Ingest Datasets CLI

Command-line interface for running the Phase 2 multilingual dataset
engineering ingestion pipelines with incremental update support,
progress tracking, and error handling.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.llm.dataset_engineering_v2 import (
    DatasetEngineeringConfig,
    DatasetEngineeringPipeline,
    DatasetReportGenerator,
    DatasetVersionManager,
    run_multilingual_ingestion,
)

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, log_file: str | None = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def build_config(args: argparse.Namespace) -> DatasetEngineeringConfig:
    ingestion = DatasetEngineeringConfig.ingestion.__class__(
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        raw_dir=args.raw_dir,
        version=args.version,
        streaming_chunk_size=args.chunk_size,
        max_documents_per_source=args.max_docs,
        incremental=args.incremental,
        resume=args.resume,
        checkpoint_interval=args.checkpoint_interval,
    )
    config = DatasetEngineeringConfig(
        seed=args.seed,
        ingestion=ingestion,
    )
    if hasattr(DatasetEngineeringConfig, "dedup"):
        config.dedup = DatasetEngineeringConfig.dedup.__class__(
            enabled=not args.no_dedup,
            use_bloom_filter=not args.no_bloom,
        )
    if hasattr(DatasetEngineeringConfig, "toxicity"):
        config.toxicity = DatasetEngineeringConfig.toxicity.__class__(
            enabled=not args.no_toxicity_filter,
            multilingual_profanity=True,
        )
    if hasattr(DatasetEngineeringConfig, "pii"):
        config.pii = DatasetEngineeringConfig.pii.__class__(
            enabled=not args.no_pii,
        )
    if hasattr(DatasetEngineeringConfig, "language"):
        config.language = DatasetEngineeringConfig.language.__class__(
            enabled=not args.no_language_detection,
            allowed_languages=args.languages.split(",") if args.languages else ["en"],
            confidence_threshold=args.confidence_threshold,
        )
    if hasattr(DatasetEngineeringConfig, "quality"):
        config.quality = DatasetEngineeringConfig.quality.__class__(
            enabled=not args.no_quality,
            min_quality_score=args.min_quality,
        )
    return config


def log_progress(
    pipeline_name: str,
    docs_processed: int,
    docs_kept: int,
    elapsed: float,
) -> None:
    docs_per_sec = docs_processed / max(elapsed, 0.001)
    retention = (docs_kept / max(docs_processed, 1)) * 100
    logger.info(
        "Progress [%s]: processed=%d, kept=%d (%.1f%%), %.1f docs/s",
        pipeline_name,
        docs_processed,
        docs_kept,
        retention,
        docs_per_sec,
    )


def run_single_pipeline(args: argparse.Namespace) -> int:
    config = build_config(args)
    pipeline = DatasetEngineeringPipeline(config)
    version_manager = DatasetVersionManager(args.versions_file)
    start = time.time()
    pipeline_names = {
        "web": "WebCrawlPipeline",
        "wiki": "WikipediaPipeline",
        "books": "BooksPipeline",
        "academic": "AcademicPipeline",
        "code": "CodePipeline",
        "math": "MathPipeline",
        "qa": "QAPipeline",
        "conversations": "ConversationPipeline",
        "ocr": "OcrPipeline",
        "image_caption": "ImageCaptionPipeline",
        "multilingual": "MultilingualPipeline",
    }
    pipeline_classes = {
        "web": pipeline.run_ingestion.__globals__.get("WebCrawlPipeline"),
        "wiki": pipeline.run_ingestion.__globals__.get("WikipediaPipeline"),
        "books": pipeline.run_ingestion.__globals__.get("BooksPipeline"),
        "academic": pipeline.run_ingestion.__globals__.get("AcademicPipeline"),
        "code": pipeline.run_ingestion.__globals__.get("CodePipeline"),
        "math": pipeline.run_ingestion.__globals__.get("MathPipeline"),
        "qa": pipeline.run_ingestion.__globals__.get("QAPipeline"),
        "conversations": pipeline.run_ingestion.__globals__.get("ConversationPipeline"),
        "ocr": pipeline.run_ingestion.__globals__.get("OcrPipeline"),
        "image_caption": pipeline.run_ingestion.__globals__.get("ImageCaptionPipeline"),
        "multilingual": pipeline.run_ingestion.__globals__.get("MultilingualPipeline"),
    }
    from models.llm.dataset_engineering_v2 import (
        AcademicPipeline,
        BooksPipeline,
        CodePipeline,
        ConversationPipeline,
        ImageCaptionPipeline,
        MathPipeline,
        MultilingualPipeline,
        OcrPipeline,
        QAPipeline,
        WebCrawlPipeline,
        WikipediaPipeline,
    )

    pipeline_classes = {
        "web": WebCrawlPipeline,
        "wiki": WikipediaPipeline,
        "books": BooksPipeline,
        "academic": AcademicPipeline,
        "code": CodePipeline,
        "math": MathPipeline,
        "qa": QAPipeline,
        "conversations": ConversationPipeline,
        "ocr": OcrPipeline,
        "image_caption": ImageCaptionPipeline,
        "multilingual": MultilingualPipeline,
    }
    selected = args.pipeline
    if selected not in pipeline_classes:
        logger.error("Unknown pipeline: %s. Available: %s", selected, ", ".join(pipeline_classes.keys()))
        return 1
    p = pipeline_classes[selected](config)
    logger.info("Running pipeline: %s", selected)
    try:
        stats = pipeline.run_ingestion(p, version_manager)
        elapsed = time.time() - start
        log_progress(selected, stats.total_documents, stats.kept_documents, elapsed)
        logger.info("Pipeline completed. Stats: %s", stats)
        return 0
    except Exception as exc:
        logger.error("Pipeline %s failed: %s", selected, exc, exc_info=args.verbose)
        return 1


def run_all_pipelines(args: argparse.Namespace) -> int:
    config = build_config(args)
    pipeline = DatasetEngineeringPipeline(config)
    version_manager = DatasetVersionManager(args.versions_file)
    selected = args.pipelines.split(",") if args.pipelines else None
    start = time.time()
    logger.info("Running all ingestion pipelines...")
    results = run_multilingual_ingestion(
        config=config,
        selected_pipelines=selected,
    )
    elapsed = time.time() - start
    total_docs = sum(s.total_documents for s in results.values())
    total_kept = sum(s.kept_documents for s in results.values())
    logger.info("All pipelines completed in %.2fs", elapsed)
    log_progress("ALL", total_docs, total_kept, elapsed)
    for name, stats in results.items():
        logger.info("  %s: %d docs, %d kept", name, stats.total_documents, stats.kept_documents)
    return 0


def list_versions(args: argparse.Namespace) -> int:
    version_manager = DatasetVersionManager(args.versions_file)
    versions = version_manager.get_versions()
    if not versions:
        logger.info("No dataset versions found.")
        return 0
    logger.info("Dataset Versions:")
    for v in versions:
        logger.info(
            "  %s | %s | %s | %d docs | %d tokens",
            v["version"],
            v["created_at"],
            v["source"],
            v["documents_count"],
            v["tokens_count"],
        )
    return 0


def generate_report(args: argparse.Namespace) -> int:
    import json

    from models.llm.dataset_engineering_v2 import DatasetEngineeringConfig, DatasetStats

    if not Path(args.stats_file).exists():
        logger.error("Stats file not found: %s", args.stats_file)
        return 1
    try:
        with open(args.stats_file, encoding="utf-8") as f:
            data = json.load(f)
        stats = DatasetStats(
            total_documents=data.get("total_documents", 0),
            kept_documents=data.get("kept_documents", 0),
            removed_exact_duplicates=data.get("removed_exact_duplicates", 0),
            removed_near_duplicates=data.get("removed_near_duplicates", 0),
            removed_toxicity=data.get("removed_toxicity", 0),
            removed_pii=data.get("removed_pii", 0),
            removed_quality=data.get("removed_quality", 0),
            removed_language=data.get("removed_language", 0),
            removed_bloom=data.get("removed_bloom", 0),
            domains=data.get("domains", {}),
            languages=Counter(data.get("languages", {})),
            token_stats=data.get("token_stats", {}),
            dataset_version=data.get("dataset_version", ""),
        )
        config = DatasetEngineeringConfig()
        report = DatasetReportGenerator(stats, config)
        output_path = report.save(args.output)
        logger.info("Report generated: %s", output_path)
        return 0
    except Exception as exc:
        logger.error("Failed to generate report: %s", exc, exc_info=True)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AstrovoxAI Phase 2 Multilingual Dataset Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all pipelines
  python scripts/ingest_datasets.py --all

  # Run specific pipeline
  python scripts/ingest_datasets.py --pipeline wiki

  # Run multiple pipelines
  python scripts/ingest_datasets.py --pipelines web,wiki,books

  # Run with custom config
  python scripts/ingest_datasets.py --all --output-dir data/processed_v2 --chunk-size 5000

  # Incremental update
  python scripts/ingest_datasets.py --all --incremental --resume

  # List dataset versions
  python scripts/ingest_datasets.py --list-versions

  # Generate report from stats
  python scripts/ingest_datasets.py --generate-report --stats-file stats.json
""",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all ingestion pipelines",
    )
    parser.add_argument(
        "--pipeline",
        type=str,
        choices=[
            "web",
            "wiki",
            "books",
            "academic",
            "code",
            "math",
            "qa",
            "conversations",
            "ocr",
            "image_caption",
            "multilingual",
        ],
        help="Run a specific pipeline",
    )
    parser.add_argument(
        "--pipelines",
        type=str,
        help="Comma-separated list of pipelines to run",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="Output directory for processed datasets",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="data/cache",
        help="Cache directory for raw downloads",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw",
        help="Raw data directory",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Dataset version tag",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=10_000,
        help="Streaming chunk size",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Maximum documents per source (None for unlimited)",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Enable incremental updates",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=50_000,
        help="Checkpoint interval",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )
    parser.add_argument(
        "--languages",
        type=str,
        default=None,
        help="Comma-separated list of allowed languages",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="Language detection confidence threshold",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.2,
        help="Minimum quality score",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Disable deduplication",
    )
    parser.add_argument(
        "--no-bloom",
        action="store_true",
        help="Disable Bloom filter",
    )
    parser.add_argument(
        "--no-toxicity-filter",
        action="store_true",
        help="Disable toxicity filtering",
    )
    parser.add_argument(
        "--no-pii",
        action="store_true",
        help="Disable PII removal",
    )
    parser.add_argument(
        "--no-language-detection",
        action="store_true",
        help="Disable language detection",
    )
    parser.add_argument(
        "--no-quality",
        action="store_true",
        help="Disable quality filtering",
    )
    parser.add_argument(
        "--versions-file",
        type=str,
        default="data/dataset_versions.json",
        help="Dataset versions file",
    )
    parser.add_argument(
        "--list-versions",
        action="store_true",
        help="List all dataset versions",
    )
    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate report from stats file",
    )
    parser.add_argument(
        "--stats-file",
        type=str,
        default="stats.json",
        help="Stats JSON file for report generation",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/dataset_report.md",
        help="Report output path",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Log file path",
    )
    args = parser.parse_args(argv)
    setup_logging(verbose=args.verbose, log_file=args.log_file)
    if args.list_versions:
        return list_versions(args)
    if args.generate_report:
        return generate_report(args)
    if args.all:
        return run_all_pipelines(args)
    if args.pipeline:
        return run_single_pipeline(args)
    if args.pipelines:
        return run_all_pipelines(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
