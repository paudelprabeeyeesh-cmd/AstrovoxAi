import json
import math
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.benchmarks.harness import BenchmarkHarness, BenchmarkReport, BenchmarkSuiteConfig
from models.llm.benchmarks.reporter import BenchmarkReporter
from models.llm.benchmarks.regression import RegressionDetector, RegressionSummary
from models.llm.benchmarks.suites import BENCHMARK_SUITES, get_suite, list_suites, build_prompt
from models.llm.evaluation.benchmarks import BENCHMARK_REGISTRY, BenchmarkResult


class MockModel:
    def __init__(self):
        self.device = "cpu"

    def eval(self):
        return self

    def train(self):
        return self

    def __call__(self, input_ids, labels=None, **kwargs):
        vocab_size = input_ids.shape[-1] if input_ids.shape[-1] > 0 else 100
        logits = input_ids.new_zeros(input_ids.shape[0], input_ids.shape[1], vocab_size)
        loss = input_ids.new_tensor(0.5) if labels is not None else None
        return {"logits": logits, "loss": loss}

    def generate(self, input_ids, max_new_tokens=64, pad_token_id=0, **kwargs):
        import torch
        new_tokens = torch.randint(0, 100, (input_ids.shape[0], max_new_tokens))
        return torch.cat([input_ids, new_tokens], dim=-1)


class MockTokenizer:
    pad_token_id = 0
    eos_token_id = 1

    def __call__(self, text, **kwargs):
        import torch
        input_ids = torch.randint(0, 100, (1, 8))
        attention_mask = torch.ones_like(input_ids)

        class _Obj:
            def __init__(self, input_ids, attention_mask):
                self.input_ids = input_ids
                self.attention_mask = attention_mask

            def to(self, device):
                return self

        return _Obj(input_ids, attention_mask)

    def decode(self, token_ids, skip_special_tokens=False):
        return "mock answer"


@pytest.fixture
def mock_model():
    return MockModel()


@pytest.fixture
def mock_tokenizer():
    return MockTokenizer()


@pytest.fixture
def harness(mock_model, mock_tokenizer):
    return BenchmarkHarness(mock_model, mock_tokenizer, model_name="test-model", device="cpu")


class TestBenchmarkHarness:
    def test_harness_initializes(self, harness):
        assert harness.model_name == "test-model"
        assert harness.device == "cpu"

    def test_run_benchmark_mmlu(self, harness, tmp_path):
        result = harness.run_benchmark("synthetic_mmlu", max_samples=2)
        assert isinstance(result, BenchmarkResult)
        assert 0.0 <= result.score <= 1.0

    def test_run_benchmark_gsm8k(self, harness):
        result = harness.run_benchmark("synthetic_gsm8k", max_samples=2)
        assert isinstance(result, BenchmarkResult)
        assert 0.0 <= result.score <= 1.0

    def test_run_unknown_benchmark_raises(self, harness):
        with pytest.raises(KeyError):
            harness.run_benchmark("nonexistent_benchmark")

    def test_evaluate_returns_report(self, harness, tmp_path):
        config = BenchmarkSuiteConfig(
            benchmarks=["synthetic_mmlu"],
            device="cpu",
            output_path=str(tmp_path / "eval.json"),
            max_samples=2,
        )
        report = harness.evaluate(config)
        assert isinstance(report, BenchmarkReport)
        assert report.model_name == "test-model"
        assert "synthetic_mmlu" in report.results

    def test_evaluate_saves_file(self, harness, tmp_path):
        config = BenchmarkSuiteConfig(
            benchmarks=["synthetic_gsm8k"],
            device="cpu",
            output_path=str(tmp_path / "eval.json"),
            max_samples=2,
        )
        harness.evaluate(config)
        assert os.path.exists(str(tmp_path / "eval.json"))

    def test_quick_eval_returns_report(self, harness):
        report = harness.quick_eval()
        assert isinstance(report, BenchmarkReport)
        assert report.model_name == "test-model"

    def test_report_summary(self, harness):
        config = BenchmarkSuiteConfig(
            benchmarks=["synthetic_mmlu"],
            device="cpu",
            max_samples=2,
        )
        report = harness.evaluate(config)
        summary = report.summary()
        assert "test-model" in summary
        assert "synthetic_mmlu" in summary


class TestBenchmarkSuites:
    def test_list_suites_returns_names(self):
        names = list_suites()
        assert isinstance(names, list)
        assert len(names) > 0
        assert "standard" in names

    def test_get_suite_standard(self):
        suite = get_suite("standard")
        assert suite.name == "standard"
        assert len(suite.benchmarks) > 0

    def test_get_unknown_suite_raises(self):
        with pytest.raises(KeyError):
            get_suite("nonexistent_suite")

    def test_suite_score_accuracy(self):
        results = {
            "mmlu": BenchmarkResult(name="mmlu", score=0.7, stderr=0.02, metadata={}),
            "gsm8k": BenchmarkResult(name="gsm8k", score=0.5, stderr=0.03, metadata={}),
        }
        suite = get_suite("standard")
        score = suite.score(results)
        assert score == pytest.approx(0.6)

    def test_build_prompt_mmlu(self):
        example = {
            "question": "What is 2+2?",
            "choices": ["3", "4", "5", "6"],
            "answer": 1,
        }
        prompt = build_prompt("mmlu", example)
        assert "What is 2+2?" in prompt
        assert "(A)" in prompt or "(B)" in prompt


class TestBenchmarkReporter:
    def test_generate_markdown_report(self, tmp_path):
        reporter = BenchmarkReporter(results_dir=str(tmp_path))
        report = {
            "model_name": "test-model",
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {
                "mmlu": {"score": 0.75, "stderr": 0.02},
                "gsm8k": {"score": 0.50, "stderr": 0.03},
            },
            "aggregate_score": 0.625,
        }
        md = reporter.generate_markdown_report(report)
        assert "test-model" in md
        assert "0.75" in md
        assert "aggregate" in md

    def test_generate_html_report(self, tmp_path):
        reporter = BenchmarkReporter(results_dir=str(tmp_path))
        report = {
            "model_name": "test-model",
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {"mmlu": {"score": 0.75, "stderr": 0.02}},
        }
        output = str(tmp_path / "report.html")
        html = reporter.generate_html_report(report, output_path=output)
        assert os.path.exists(output)
        assert "<!DOCTYPE html>" in html
        assert "0.75" in html

    def test_generate_comparison_markdown(self, tmp_path):
        reporter = BenchmarkReporter(results_dir=str(tmp_path))
        reports = [
            {
                "model_name": "model-a",
                "results": {"mmlu": {"score": 0.7}, "gsm8k": {"score": 0.5}},
            },
            {
                "model_name": "model-b",
                "results": {"mmlu": {"score": 0.75}, "gsm8k": {"score": 0.55}},
            },
        ]
        md = reporter.generate_comparison_markdown(reports)
        assert "model-a" in md
        assert "model-b" in md
        assert "0.75" in md

    def test_load_report(self, tmp_path):
        reporter = BenchmarkReporter(results_dir=str(tmp_path))
        report = {
            "model_name": "test",
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {"mmlu": {"score": 0.7, "stderr": 0.01}},
        }
        with open(tmp_path / "test.json", "w") as f:
            json.dump(report, f)
        loaded = reporter.load_report(str(tmp_path / "test.json"))
        assert loaded["model_name"] == "test"
        assert loaded["results"]["mmlu"]["score"] == 0.7


class TestRegressionDetection:
    def test_compare_no_regression(self, tmp_path):
        detector = RegressionDetector(results_dir=str(tmp_path))
        baseline = {
            "model_name": "baseline",
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {"mmlu": {"score": 0.7, "stderr": 0.02}},
        }
        current = {
            "model_name": "current",
            "timestamp": "2024-01-02T00:00:00Z",
            "results": {"mmlu": {"score": 0.72, "stderr": 0.02}},
        }
        baseline_path = str(tmp_path / "baseline.json")
        current_path = str(tmp_path / "current.json")
        with open(baseline_path, "w") as f:
            json.dump(baseline, f)
        with open(current_path, "w") as f:
            json.dump(current, f)

        summary = detector.compare(baseline_path, current_path)
        assert not summary.has_regression
        assert summary.regression_count == 0

    def test_compare_detects_regression(self, tmp_path):
        detector = RegressionDetector(results_dir=str(tmp_path), regression_threshold=-0.01)
        baseline = {
            "model_name": "baseline",
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {"mmlu": {"score": 0.7, "stderr": 0.02}},
        }
        current = {
            "model_name": "current",
            "timestamp": "2024-01-02T00:00:00Z",
            "results": {"mmlu": {"score": 0.65, "stderr": 0.02}},
        }
        baseline_path = str(tmp_path / "baseline.json")
        current_path = str(tmp_path / "current.json")
        with open(baseline_path, "w") as f:
            json.dump(baseline, f)
        with open(current_path, "w") as f:
            json.dump(current, f)

        summary = detector.compare(baseline_path, current_path)
        assert summary.has_regression
        assert summary.regression_count == 1
        assert summary.diffs[0].relative_change < 0

    def test_save_summary(self, tmp_path):
        detector = RegressionDetector(results_dir=str(tmp_path))
        summary = RegressionSummary(
            baseline_model="baseline",
            current_model="current",
            diffs=[],
            has_regression=False,
            regression_count=0,
            improvement_count=1,
            timestamp="2024-01-02T00:00:00Z",
        )
        path = detector.save_summary(summary)
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["has_regression"] is False

    def test_generate_markdown_report(self, tmp_path):
        detector = RegressionDetector(results_dir=str(tmp_path))
        summary = RegressionSummary(
            baseline_model="baseline",
            current_model="current",
            diffs=[],
            has_regression=False,
            regression_count=0,
            improvement_count=0,
            timestamp="2024-01-02T00:00:00Z",
        )
        md = detector.generate_markdown_report(summary)
        assert "Regression Analysis Report" in md
        assert "baseline" in md


class TestBenchmarkRegistry:
    def test_registry_has_expected_benchmarks(self):
        expected = ["mmlu", "hellaswag", "arc", "gsm8k", "humaneval", "mbpp", "truthfulqa", "winogrande", "piqa"]
        for name in expected:
            assert name in BENCHMARK_REGISTRY, f"Missing benchmark: {name}"

    def test_registry_instantiation(self):
        for name, cls in BENCHMARK_REGISTRY.items():
            instance = cls(max_samples=10)
            assert hasattr(instance, "run")
