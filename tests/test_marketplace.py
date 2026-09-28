import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from models.llm.marketplace.models import ModelMarketplace, ModelLicense, ModelVisibility
from models.llm.marketplace.datasets import DatasetMarketplace, DatasetLicense as DLicense, DatasetVisibility as DVis
from models.llm.marketplace.loras import LoRAMarketplace, LoRACompatibility
from models.llm.marketplace.benchmarks import BenchmarkManager
from models.llm.marketplace.prompts import PromptMarketplace, PromptVisibility as PVis


@pytest.fixture
def tmp_model_file():
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(b"fake model weights")
        path = f.name
    yield path
    os.remove(path)


@pytest.fixture
def tmp_dataset_file():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        f.write(b'{"text": "sample"}\n')
        path = f.name
    yield path
    os.remove(path)


@pytest.fixture
def tmp_lora_file():
    with tempfile.NamedTemporaryFile(suffix=".safetensors", delete=False) as f:
        f.write(b"fake lora weights")
        path = f.name
    yield path
    os.remove(path)


class TestModelMarketplace:
    def test_upload_model(self, tmp_model_file):
        mp = ModelMarketplace(storage_dir=tempfile.mkdtemp())
        model = mp.upload_model(
            name="TestModel",
            author_id="user1",
            description="A test model",
            version="v1.0.0",
            file_path=tmp_model_file,
            license=ModelLicense.MIT,
        )
        assert model.name == "TestModel"
        assert model.author_id == "user1"
        assert "v1.0.0" in model.versions

    def test_add_version(self, tmp_model_file):
        mp = ModelMarketplace(storage_dir=tempfile.mkdtemp())
        model = mp.upload_model(
            name="TestModel",
            author_id="user1",
            description="A test model",
            version="v1.0.0",
            file_path=tmp_model_file,
            license=ModelLicense.MIT,
        )
        model_id = model.model_id
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"updated weights")
            path = f.name
        try:
            version = mp.add_version(model_id, "v2.0.0", path, "Updated version")
            assert version.version == "v2.0.0"
            assert model.versions["v2.0.0"].version == "v2.0.0"
        finally:
            os.remove(path)

    def test_download_model(self, tmp_model_file):
        mp = ModelMarketplace(storage_dir=tempfile.mkdtemp())
        model = mp.upload_model(
            name="TestModel",
            author_id="user1",
            description="A test model",
            version="v1.0.0",
            file_path=tmp_model_file,
            license=ModelLicense.MIT,
        )
        downloaded = mp.download_model(model.model_id)
        assert downloaded.download_count == 1

    def test_rate_model(self, tmp_model_file):
        mp = ModelMarketplace(storage_dir=tempfile.mkdtemp())
        model = mp.upload_model(
            name="TestModel",
            author_id="user1",
            description="A test model",
            version="v1.0.0",
            file_path=tmp_model_file,
            license=ModelLicense.MIT,
        )
        rating = mp.rate_model(model.model_id, "user2", 5, "Excellent")
        assert rating.score == 5
        assert len(mp.get_model(model.model_id).ratings) == 1

    def test_search_models(self, tmp_model_file):
        mp = ModelMarketplace(storage_dir=tempfile.mkdtemp())
        mp.upload_model(
            name="AlphaModel",
            author_id="user1",
            description="First model",
            version="v1.0.0",
            file_path=tmp_model_file,
            license=ModelLicense.MIT,
            tags=["nlp"],
        )
        results = mp.search_models(query="Alpha")
        assert len(results) == 1
        results = mp.search_models(tags=["nlp"])
        assert len(results) == 1
        results = mp.search_models(min_rating=4.0)
        assert len(results) == 0

    def test_search_models_with_rating(self, tmp_model_file):
        mp = ModelMarketplace(storage_dir=tempfile.mkdtemp())
        model = mp.upload_model(
            name="RatedModel",
            author_id="user1",
            description="Rated model",
            version="v1.0.0",
            file_path=tmp_model_file,
            license=ModelLicense.MIT,
        )
        mp.rate_model(model.model_id, "user2", 5)
        mp.rate_model(model.model_id, "user3", 5)
        results = mp.search_models(min_rating=4.5)
        assert len(results) == 1


class TestDatasetMarketplace:
    def test_upload_dataset(self, tmp_dataset_file):
        dm = DatasetMarketplace(storage_dir=tempfile.mkdtemp())
        ds = dm.upload_dataset(
            name="TestDataset",
            author_id="user1",
            description="A test dataset",
            version="v1.0.0",
            file_path=tmp_dataset_file,
            license=DLicense.CC_BY,
            format="jsonl",
        )
        assert ds.name == "TestDataset"
        assert "v1.0.0" in ds.versions

    def test_set_quality_score(self, tmp_dataset_file):
        dm = DatasetMarketplace(storage_dir=tempfile.mkdtemp())
        ds = dm.upload_dataset(
            name="TestDataset",
            author_id="user1",
            description="A test dataset",
            version="v1.0.0",
            file_path=tmp_dataset_file,
            license=DLicense.CC_BY,
            format="jsonl",
        )
        score = dm.set_quality_score(
            ds.dataset_id, "v1.0.0",
            overall=0.9, completeness=0.95, consistency=0.85,
            accuracy=0.9, diversity=0.88, noise_ratio=0.05,
        )
        assert score.overall == 0.9

    def test_search_datasets(self, tmp_dataset_file):
        dm = DatasetMarketplace(storage_dir=tempfile.mkdtemp())
        dm.upload_dataset(
            name="AlphaDataset",
            author_id="user1",
            description="First dataset",
            version="v1.0.0",
            file_path=tmp_dataset_file,
            license=DLicense.CC_BY,
            tags=["text"],
        )
        results = dm.search_datasets(query="Alpha")
        assert len(results) == 1


class TestLoRAMarketplace:
    def test_upload_lora(self, tmp_lora_file):
        lm = LoRAMarketplace(storage_dir=tempfile.mkdtemp())
        lora = lm.upload_lora(
            name="TestLoRA",
            author_id="user1",
            description="A test LoRA",
            version="v1.0.0",
            file_path=tmp_lora_file,
            base_model="llama-2-7b",
            rank=8,
            alpha=16,
            target_modules=["q_proj", "v_proj"],
        )
        assert lora.name == "TestLoRA"
        assert lora.base_model == "llama-2-7b"

    def test_check_compatibility(self, tmp_lora_file):
        lm = LoRAMarketplace(storage_dir=tempfile.mkdtemp())
        lora = lm.upload_lora(
            name="TestLoRA",
            author_id="user1",
            description="A test LoRA",
            version="v1.0.0",
            file_path=tmp_lora_file,
            base_model="llama-2-7b",
            rank=8,
            alpha=16,
            target_modules=["q_proj"],
        )
        assert lm.check_compatibility(lora.lora_id, "llama-2-7b") == LoRACompatibility.COMPATIBLE
        assert lm.check_compatibility(lora.lora_id, "llama-2-13b") == LoRACompatibility.INCOMPATIBLE

    def test_search_loras(self, tmp_lora_file):
        lm = LoRAMarketplace(storage_dir=tempfile.mkdtemp())
        lm.upload_lora(
            name="AlphaLoRA",
            author_id="user1",
            description="A LoRA",
            version="v1.0.0",
            file_path=tmp_lora_file,
            base_model="llama-2-7b",
            rank=8,
            alpha=16,
            target_modules=["q_proj"],
        )
        results = lm.search_loras(base_model="llama-2-7b")
        assert len(results) == 1


class TestBenchmarkManager:
    def test_create_and_submit(self):
        bm = BenchmarkManager()
        bench = bm.create_benchmark(
            name="MMLU",
            description="Massive Multitask Language Understanding",
            metrics=["accuracy", "f1"],
            owner_id="admin",
        )
        assert bench.name == "MMLU"
        submission = bm.submit_result(
            benchmark_id=bench.benchmark_id,
            submitter_id="user1",
            model_id="model-1",
            results={"accuracy": 0.85, "f1": 0.83},
        )
        assert submission.results["accuracy"] == 0.85

    def test_generate_leaderboard(self):
        bm = BenchmarkManager()
        bench = bm.create_benchmark(
            name="MMLU",
            description="Massive Multitask Language Understanding",
            metrics=["accuracy"],
            owner_id="admin",
        )
        bm.submit_result(bench.benchmark_id, "user1", "model-a", {"accuracy": 0.8})
        bm.submit_result(bench.benchmark_id, "user2", "model-b", {"accuracy": 0.9})
        leaderboard = bm.generate_leaderboard(bench.benchmark_id, "accuracy")
        assert leaderboard[0]["model_id"] == "model-b"
        assert leaderboard[0]["score"] == 0.9


class TestPromptMarketplace:
    def test_share_and_search(self):
        pm = PromptMarketplace()
        prompt = pm.share_prompt(
            title="Summarizer",
            author_id="user1",
            description="Summarizes text",
            content="Summarize: {text}",
            visibility=PVis.PUBLIC,
            tags=["summarization"],
        )
        assert prompt.title == "Summarizer"
        results = pm.search_prompts(query="Summar")
        assert len(results) == 1

    def test_render_template(self):
        pm = PromptMarketplace()
        prompt = pm.share_prompt(
            title="Greeter",
            author_id="user1",
            description="Greets user",
            content="Hello {name}!",
            templates=[{
                "content": "Hello {name}!",
                "variables": ["name"],
                "description": "Greeting template",
            }],
        )
        rendered = pm.render_template(prompt.prompt_id, prompt.templates[0].template_id, {"name": "World"})
        assert rendered == "Hello World!"
