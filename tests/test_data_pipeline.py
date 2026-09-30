from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.data import (
    CopyrightConfig,
    CopyrightFilter,
    DataLineageTracker,
    DatasetPipeline,
    DatasetVersionManager,
    Deduplicator,
    DomainBalancer,
    DomainBalanceConfig,
    LanguageBalanceConfig,
    LanguageBalancer,
    PIIDetector,
    PipelineConfig,
    PiiConfig,
    QualityConfig,
    QualityScorer,
    ToxicityConfig,
    ToxicityFilter,
    VersionConfig,
)
from models.llm.dataset_engineering_v2 import ProcessedDocument


class TestQualityScorer:
    def test_length_score_short_text(self):
        scorer = QualityScorer(QualityConfig(min_length=10))
        assert scorer.length_score("short") < 1.0

    def test_length_score_ideal(self):
        config = QualityConfig(min_length=1, max_length=100_000)
        scorer = QualityScorer(config)
        score = scorer.length_score("word " * 50)
        assert score > 0.5

    def test_language_confidence_score(self):
        scorer = QualityScorer()
        assert scorer.language_confidence_score(0.0) == 0.0
        assert scorer.language_confidence_score(1.0) == 1.0
        assert scorer.language_confidence_score(1.5) == 1.0

    def test_repetition_score(self):
        scorer = QualityScorer()
        good = scorer.repetition_score("the quick brown fox jumps over the lazy dog")
        bad = scorer.repetition_score("the the the the the")
        assert good > bad

    def test_entropy_score(self):
        scorer = QualityScorer()
        high = scorer.entropy_score("the quick brown fox jumps over the lazy dog")
        low = scorer.entropy_score("the the the the the")
        assert high > low

    def test_score_returns_range(self):
        scorer = QualityScorer()
        doc = ProcessedDocument(text="This is a normal English sentence with enough words.")
        doc.language_confidence = 0.9
        score = scorer.score(doc)
        assert 0.0 <= score <= 1.0

    def test_passes_threshold(self):
        config = QualityConfig(min_quality_score=0.5, min_length=5)
        scorer = QualityScorer(config)
        doc = ProcessedDocument(text="This is a normal English sentence with enough words.")
        doc.language_confidence = 0.9
        assert scorer.passes(doc) is True

    def test_process_returns_none_for_bad_doc(self):
        scorer = QualityScorer(QualityConfig(min_quality_score=0.9))
        doc = ProcessedDocument(text="the the the the the")
        doc.language_confidence = 0.9
        result = scorer.process(doc)
        assert result is None

    def test_process_returns_doc_for_good_doc(self):
        scorer = QualityScorer(QualityConfig(min_quality_score=0.1, min_length=5))
        doc = ProcessedDocument(text="This is a normal English sentence with enough words.")
        doc.language_confidence = 0.9
        result = scorer.process(doc)
        assert result is not None
        assert result.quality_score > 0.0


class TestCopyrightFilter:
    def test_allows_clean_text(self):
        f = CopyrightFilter()
        doc = ProcessedDocument(text="This is a clean sentence about science.")
        assert f.process(doc) is not None

    def test_removes_copyrighted_text(self):
        f = CopyrightFilter(CopyrightConfig(max_copyright_matches=1))
        doc = ProcessedDocument(
            text="All rights reserved. Copyright 2024. All rights reserved."
        )
        assert f.process(doc) is None

    def test_disabled_passes_all(self):
        f = CopyrightFilter(CopyrightConfig(enabled=False))
        doc = ProcessedDocument(text="All rights reserved. Copyright 2024.")
        assert f.process(doc) is not None


class TestPIIDetector:
    def test_removes_email(self):
        pii = PIIDetector()
        doc = ProcessedDocument(text="Contact me at test@example.com for details.")
        result = pii.process(doc)
        assert "[REDACTED]" in result.text

    def test_removes_phone(self):
        pii = PIIDetector()
        doc = ProcessedDocument(text="Call me at 555-123-4567 today.")
        result = pii.process(doc)
        assert "[REDACTED]" in result.text

    def test_disabled_no_removal(self):
        pii = PIIDetector(PiiConfig(enabled=False))
        doc = ProcessedDocument(text="Contact me at test@example.com")
        result = pii.process(doc)
        assert "test@example.com" in result.text


class TestToxicityFilter:
    def test_allows_clean_text(self):
        tf = ToxicityFilter()
        doc = ProcessedDocument(text="This is a nice and friendly message.")
        assert tf.process(doc) is not None

    def test_removes_toxic_text(self):
        tf = ToxicityFilter(ToxicityConfig(max_toxicity_score=0.01))
        doc = ProcessedDocument(text="This is a fuck shit message.")
        assert tf.process(doc) is None


class TestDeduplicator:
    def test_removes_exact_duplicate(self):
        d = Deduplicator()
        doc1 = ProcessedDocument(text="the quick brown fox jumps over the lazy dog")
        doc2 = ProcessedDocument(text="the quick brown fox jumps over the lazy dog")
        r1 = d.process(doc1)
        r2 = d.process(doc2)
        assert r1 is not None
        assert "duplicate" not in r1.metadata
        assert r2 is not None
        assert r2.metadata.get("duplicate") == "exact"

    def test_keeps_unique(self):
        d = Deduplicator()
        doc1 = ProcessedDocument(text="the quick brown fox jumps over the lazy dog")
        doc2 = ProcessedDocument(text="a completely different sentence about cats and dogs")
        assert d.process(doc1) is not None
        r2 = d.process(doc2)
        assert r2 is not None
        assert "duplicate" not in r2.metadata

    def test_stream_deduplication(self):
        d = Deduplicator()
        docs = [
            ProcessedDocument(text="same text here"),
            ProcessedDocument(text="same text here"),
            ProcessedDocument(text="different text"),
        ]
        kept, removed = d.process_stream(docs)
        assert len(kept) == 2
        assert len(removed) == 1


class TestLanguageBalancer:
    def test_distributes_documents(self):
        config = LanguageBalanceConfig(
            target_ratios={"en": 0.5, "es": 0.5},
            seed=42,
        )
        balancer = LanguageBalancer(config)
        for _ in range(10):
            doc = ProcessedDocument(text="hello world", language="en")
            balancer.add(doc)
        for _ in range(10):
            doc = ProcessedDocument(text="hola mundo", language="es")
            balancer.add(doc)
        sample = balancer.sample()
        assert len(sample) == 20

    def test_distribution_tracks_counts(self):
        balancer = LanguageBalancer()
        balancer.add(ProcessedDocument(text="hello", language="en"))
        balancer.add(ProcessedDocument(text="hola", language="es"))
        dist = balancer.distribution()
        assert abs(dist["en"] - 0.5) < 0.01
        assert abs(dist["es"] - 0.5) < 0.01


class TestDomainBalancer:
    def test_distributes_by_domain(self):
        config = DomainBalanceConfig(
            target_ratios={"web": 0.5, "wiki": 0.5},
            seed=42,
        )
        balancer = DomainBalancer(config)
        for _ in range(10):
            doc = ProcessedDocument(text="web content", domain="web")
            balancer.add(doc)
        for _ in range(10):
            doc = ProcessedDocument(text="wiki content", domain="wiki")
            balancer.add(doc)
        sample = balancer.sample()
        assert len(sample) == 20

    def test_empty_sample(self):
        balancer = DomainBalancer()
        assert balancer.sample() == []


class TestDatasetVersionManager:
    def test_creates_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vm = DatasetVersionManager(VersionConfig(versions_file=os.path.join(tmpdir, "versions.json")))
            entry = vm.create_version(
                source="test",
                documents_count=100,
                tokens_count=5000,
                config={"quality": {"min_score": 0.2}},
            )
            assert entry["version"]
            assert entry["documents_count"] == 100
            assert entry["tokens_count"] == 5000

    def test_get_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vm = DatasetVersionManager(VersionConfig(versions_file=os.path.join(tmpdir, "versions.json")))
            vm.create_version(source="a", documents_count=10, tokens_count=100)
            latest = vm.get_latest()
            assert latest is not None
            assert latest["source"] == "a"

    def test_get_versions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vm = DatasetVersionManager(VersionConfig(versions_file=os.path.join(tmpdir, "versions.json")))
            vm.create_version(source="a", documents_count=10, tokens_count=100)
            vm.create_version(source="b", documents_count=20, tokens_count=200)
            versions = vm.get_versions()
            assert len(versions) == 2


class TestDataLineageTracker:
    def test_records_stages(self):
        tracker = DataLineageTracker(output_dir=tempfile.mkdtemp())
        tracker.record("ingest", input_count=100, output_count=100, duration_seconds=0.5)
        tracker.record("filter", input_count=100, output_count=80, duration_seconds=0.3)
        summary = tracker.summary()
        assert summary["stages"] == 2
        assert summary["total_input"] == 200
        assert summary["total_output"] == 180
        assert summary["total_removed"] == 20

    def test_saves_lineage(self):
        tmpdir = tempfile.mkdtemp()
        tracker = DataLineageTracker(output_dir=tmpdir)
        tracker.record("ingest", input_count=50, output_count=50, duration_seconds=0.1)
        path = tracker.save()
        assert path.exists()
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1


class TestDatasetPipeline:
    def test_run_returns_stats(self):
        config = PipelineConfig(chunk_size=10, enable_progress=False)
        pipeline = DatasetPipeline(config)
        docs = [
            ProcessedDocument(text=f"document number {i} with enough words to pass quality")
            for i in range(5)
        ]
        results = list(pipeline.run(iter(docs)))
        assert len(results) == 5
        assert pipeline.context.processed == 5

    def test_register_custom_stage(self):
        config = PipelineConfig(chunk_size=10, enable_progress=False)
        pipeline = DatasetPipeline(config)

        def upper_stage(ctx, documents):
            for doc in documents:
                doc.text = doc.text.upper()
            return documents

        pipeline.register_stage("uppercase", upper_stage)
        docs = [ProcessedDocument(text="hello world test")]
        results = list(pipeline.run(iter(docs)))
        assert results[0].text == "HELLO WORLD TEST"

    def test_run_stream_produces_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jsonl")
            output_path = os.path.join(tmpdir, "output.jsonl")
            with open(input_path, "w", encoding="utf-8") as f:
                for i in range(10):
                    doc = {
                        "text": f"document number {i} with enough words to pass quality checks",
                        "source": "test",
                        "domain": "web",
                    }
                    f.write(json.dumps(doc) + "\n")
            config = PipelineConfig(chunk_size=10, enable_progress=False)
            pipeline = DatasetPipeline(config)
            stats = pipeline.run_stream(input_path, output_path)
            assert stats["total_processed"] == 10
            assert stats["kept"] > 0
            assert os.path.exists(output_path)
