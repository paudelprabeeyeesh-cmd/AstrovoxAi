
import pytest
from unittest.mock import patch, MagicMock
from tests.benchmark import BenchmarkRunner, LocalDatasetLoader


class TestBenchmarks:
    def test_local_dataset_loader(self):
        loader = LocalDatasetLoader()
        data = loader.load(sample_size=5)
        assert "mmlu" in data
        assert "humaneval" in data
        assert "gsm8k" in data
        assert "truthfulqa" in data
        assert len(data["mmlu"]) == 5

    @patch("tests.benchmark.LLMClient")
    def test_benchmark_runner_mmlu(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.generate.return_value = "Paris"
        mock_llm_cls.return_value = mock_client
        runner = BenchmarkRunner(model_fn=None, use_llm_judge=False)
        result = runner.run_mmlu(sample_size=2)
        assert result.benchmark == "mmlu"
        assert result.sample_count == 2

    @patch("tests.benchmark.LLMClient")
    def test_benchmark_runner_humaneval(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.generate.return_value = "def add(a, b):\n    return a + b"
        mock_llm_cls.return_value = mock_client
        runner = BenchmarkRunner(model_fn=None, use_llm_judge=False)
        result = runner.run_humaneval(sample_size=2)
        assert result.benchmark == "humaneval"

    @patch("tests.benchmark.LLMClient")
    def test_benchmark_runner_gsm8k(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.generate.return_value = "3"
        mock_llm_cls.return_value = mock_client
        runner = BenchmarkRunner(model_fn=None, use_llm_judge=False)
        result = runner.run_gsm8k(sample_size=2)
        assert result.benchmark == "gsm8k"

    @patch("tests.benchmark.LLMClient")
    def test_benchmark_runner_truthfulqa(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.generate.return_value = "No"
        mock_llm_cls.return_value = mock_client
        runner = BenchmarkRunner(model_fn=None, use_llm_judge=False)
        result = runner.run_truthfulqa(sample_size=2)
        assert result.benchmark == "truthfulqa"

    @patch("tests.benchmark.LLMClient")
    def test_benchmark_runner_run_all(self, mock_llm_cls):
        mock_client = MagicMock()
        mock_client.generate.return_value = "mock answer"
        mock_llm_cls.return_value = mock_client
        runner = BenchmarkRunner(model_fn=None, use_llm_judge=False)
        results = runner.run_all(sample_size=2)
        assert len(results) == 4
        assert all(r.sample_count == 2 for r in results.values())
