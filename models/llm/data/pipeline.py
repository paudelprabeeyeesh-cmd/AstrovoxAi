from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from models.llm.dataset_engineering_v2 import (
    ProcessedDocument,
    TextUtils,
    DatasetIO,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    chunk_size: int = 10_000
    seed: int = 42
    enable_progress: bool = True
    progress_interval: int = 5_000


StageFn = Callable[["PipelineContext", list[ProcessedDocument]], list[ProcessedDocument]]


@dataclass
class PipelineContext:
    config: PipelineConfig
    stats: dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    processed: int = 0
    kept: int = 0
    removed: int = 0

    def __post_init__(self) -> None:
        self.start_time = time.time()

    def record(self, key: str, value: Any) -> None:
        self.stats[key] = value

    def increment(self, key: str, amount: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + amount

    def elapsed(self) -> float:
        return time.time() - self.start_time

    def throughput(self) -> float:
        elapsed = self.elapsed()
        return self.processed / elapsed if elapsed > 0 else 0.0


class DatasetPipeline:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.context = PipelineContext(config=config)
        self._stages: list[tuple[str, StageFn]] = []
        self._register_default_stages()

    def _register_default_stages(self) -> None:
        self._stages = [
            ("ingest", self._stage_ingest),
            ("clean", self._stage_clean),
            ("filter", self._stage_filter),
            ("deduplicate", self._stage_deduplicate),
            ("balance", self._stage_balance),
            ("version", self._stage_version),
        ]

    def register_stage(self, name: str, fn: StageFn) -> None:
        self._stages.append((name, fn))

    def _stage_ingest(
        self, ctx: PipelineContext, documents: list[ProcessedDocument]
    ) -> list[ProcessedDocument]:
        ctx.record("ingested", len(documents))
        return documents

    def _stage_clean(
        self, ctx: PipelineContext, documents: list[ProcessedDocument]
    ) -> list[ProcessedDocument]:
        cleaned: list[ProcessedDocument] = []
        for doc in documents:
            doc.text = TextUtils.clean_text(doc.text)
            doc.token_count = TextUtils.count_tokens(doc.text)
            cleaned.append(doc)
        ctx.record("cleaned", len(cleaned))
        return cleaned

    def _stage_filter(
        self, ctx: PipelineContext, documents: list[ProcessedDocument]
    ) -> list[ProcessedDocument]:
        filtered: list[ProcessedDocument] = []
        for doc in documents:
            if not doc.text.strip():
                continue
            if len(doc.text.split()) < 3:
                continue
            filtered.append(doc)
        ctx.record("filtered", len(filtered))
        return filtered

    def _stage_deduplicate(
        self, ctx: PipelineContext, documents: list[ProcessedDocument]
    ) -> list[ProcessedDocument]:
        seen: set[str] = set()
        deduped: list[ProcessedDocument] = []
        for doc in documents:
            normalized = TextUtils.normalize(doc.text)
            doc_hash = TextUtils.sha256(normalized)
            if doc_hash in seen:
                ctx.increment("removed_duplicates")
                continue
            seen.add(doc_hash)
            doc.dedup_hash = doc_hash
            deduped.append(doc)
        ctx.record("deduplicated", len(deduped))
        return deduped

    def _stage_balance(
        self, ctx: PipelineContext, documents: list[ProcessedDocument]
    ) -> list[ProcessedDocument]:
        ctx.record("balanced", len(documents))
        return documents

    def _stage_version(
        self, ctx: PipelineContext, documents: list[ProcessedDocument]
    ) -> list[ProcessedDocument]:
        ctx.record("versioned", len(documents))
        return documents

    def _log_progress(self, ctx: PipelineContext) -> None:
        if not self.config.enable_progress:
            return
        if ctx.processed % self.config.progress_interval == 0 and ctx.processed > 0:
            logger.info(
                "Progress: %d processed, %d kept, %.1f docs/s",
                ctx.processed,
                ctx.kept,
                ctx.throughput(),
            )

    def run(self, documents: Iterator[ProcessedDocument]) -> Iterator[ProcessedDocument]:
        chunk: list[ProcessedDocument] = []
        for doc in documents:
            chunk.append(doc)
            ctx = self.context
            ctx.processed += 1
            if len(chunk) >= self.config.chunk_size:
                yield from self._process_chunk(chunk)
                chunk = []
                self._log_progress(ctx)
        if chunk:
            yield from self._process_chunk(chunk)
            self._log_progress(self.context)

    def _process_chunk(
        self, documents: list[ProcessedDocument]
    ) -> Iterator[ProcessedDocument]:
        current = documents
        for stage_name, stage_fn in self._stages:
            current = stage_fn(self.context, current)
            if not current:
                break
        self.context.kept += len(current)
        self.context.removed += len(documents) - len(current)
        yield from current

    def run_stream(
        self,
        input_path: str | Path,
        output_path: str | Path,
        text_field: str = "text",
        source_field: str = "source",
        domain_field: str = "domain",
    ) -> dict[str, Any]:
        start = time.time()
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        buffer: list[ProcessedDocument] = []
        for doc in DatasetIO.iter_documents(
            input_path,
            text_field=text_field,
            source_field=source_field,
            domain_field=domain_field,
            chunk_size=self.config.chunk_size,
        ):
            buffer.append(doc)
            if len(buffer) >= self.config.chunk_size:
                for processed in self.run(buffer):
                    buffer = [processed]
                DatasetIO.write_jsonl(buffer, output)
                buffer = []
        if buffer:
            for processed in self.run(buffer):
                buffer = [processed]
            DatasetIO.write_jsonl(buffer, output)
        elapsed = time.time() - start
        stats = {
            "total_processed": self.context.processed,
            "kept": self.context.kept,
            "removed": self.context.removed,
            "elapsed_seconds": elapsed,
            "throughput_docs_per_sec": self.context.throughput(),
            "pipeline_stats": dict(self.context.stats),
        }
        logger.info(
            "Pipeline complete: %d docs in %.2fs (%.1f docs/s)",
            self.context.processed,
            elapsed,
            self.context.throughput(),
        )
        return stats
