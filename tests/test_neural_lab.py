import json
import threading

import pytest
import torch

from neural_lab.config import TinyTransformerConfig
from neural_lab.datasets import DatasetStore
from neural_lab.evaluation import evaluate_checkpoint, generate_text, write_evaluation_report
from neural_lab.experiments import list_experiments
from neural_lab.mlp import MultilayerPerceptron
from neural_lab.model import TinyTransformer
from neural_lab.registry import ModelRegistry
from neural_lab.resources import MemoryEstimate, enforce_memory_budget, estimate_training_memory
from neural_lab.tokenizer import CharacterTokenizer
from neural_lab.training import _make_optimizer, train_tiny_model


def test_character_tokenizer_round_trip_and_rejects_unknown():
    tokenizer = CharacterTokenizer(["a", "b", " "])
    assert tokenizer.decode(tokenizer.encode("ab a")) == "ab a"
    with pytest.raises(ValueError):
        tokenizer.encode("c")


def test_tokenizer_streams_small_utf8_file(tmp_path):
    source = tmp_path / "text.txt"
    source.write_text("héllo", encoding="utf-8")
    tokenizer = CharacterTokenizer.from_file(source)
    assert tokenizer.decode(tokenizer.encode("héllo")) == "héllo"
    with pytest.raises(ValueError, match="configured limit"):
        CharacterTokenizer.from_file(source, max_file_bytes=2)


def test_character_vocabulary_limit_rejects_pathological_unicode_input(tmp_path):
    source = tmp_path / "wide-vocabulary.txt"
    source.write_text("".join(chr(0x4000 + index) for index in range(4097)), encoding="utf-8")
    with pytest.raises(ValueError, match="safety limit"):
        CharacterTokenizer.from_file(source)
    with pytest.raises(ValueError, match="unique characters"):
        DatasetStore(tmp_path / "datasets").add_file(source)


def test_dataset_store_validates_deduplicates_and_requires_delete_confirmation(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"approved small text\n")
    store = DatasetStore(tmp_path / "datasets")
    first = store.add_file(source, provenance="User supplied", license_note="User owns the text")
    duplicate = store.add_file(source, provenance="Different note", license_note="Different note")
    assert duplicate["dataset_id"] == first["dataset_id"]
    assert first["character_count"] == len("approved small text\n")
    assert store.get_path(first["dataset_id"]).parent == (tmp_path / "datasets").resolve()
    assert len(store.list_datasets()) == 1
    with pytest.raises(PermissionError, match="confirmed=True"):
        store.delete(first["dataset_id"])
    store.delete(first["dataset_id"], confirmed=True)
    assert store.list_datasets() == []


def test_dataset_store_rejects_empty_and_oversized_input(tmp_path):
    store = DatasetStore(tmp_path / "datasets", max_file_bytes=10)
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        store.add_file(empty)
    large = tmp_path / "large.txt"
    large.write_text("x" * 11, encoding="utf-8")
    with pytest.raises(ValueError, match="limit"):
        store.add_file(large)


def test_transformer_shapes_loss_and_autograd():
    config = TinyTransformerConfig(vocab_size=11, context_length=8, hidden_size=8, num_heads=2)
    model = TinyTransformer(config)
    tokens = torch.randint(0, 11, (2, 7))
    logits, loss = model(tokens, tokens)
    assert logits.shape == (2, 7, 11)
    assert loss is not None and torch.isfinite(loss)
    loss.backward()
    assert any(p.grad is not None and torch.count_nonzero(p.grad) for p in model.parameters())


def test_transformer_rejects_invalid_dimensions_and_context():
    with pytest.raises(ValueError, match="divisible"):
        TinyTransformerConfig(vocab_size=8, hidden_size=7, num_heads=2)
    model = TinyTransformer(TinyTransformerConfig(vocab_size=8, context_length=4, hidden_size=8, num_heads=2))
    with pytest.raises(ValueError, match="context_length"):
        model(torch.ones((1, 5), dtype=torch.long))


def test_mlp_layers_weights_biases_activations_and_gradients():
    network = MultilayerPerceptron(4, (8, 6), 3, activation="tanh")
    inputs = torch.randn(5, 4)
    logits = network(inputs)
    loss = torch.nn.functional.cross_entropy(logits, torch.tensor([0, 1, 2, 0, 1]))
    loss.backward()
    linear_layers = [layer for layer in network.modules() if isinstance(layer, torch.nn.Linear)]
    assert logits.shape == (5, 3)
    assert len(linear_layers) == 3
    assert all(layer.bias is not None and layer.weight.grad is not None for layer in linear_layers)
    with pytest.raises(ValueError, match="last dimension"):
        network(torch.randn(5, 5))
    with pytest.raises(ValueError, match="activation"):
        MultilayerPerceptron(2, (3,), 1, activation="invalid")


def test_generation_validates_top_k_and_returns_tokens():
    model = TinyTransformer(TinyTransformerConfig(vocab_size=8, context_length=4, hidden_size=8, num_heads=2))
    generated = model.generate(torch.tensor([[1, 2]]), max_new_tokens=2, top_k=2)
    assert generated.shape == (1, 4)
    with pytest.raises(ValueError, match="top_k"):
        model.generate(torch.tensor([[1]]), top_k=9)
    with pytest.raises(ValueError, match="temperature"):
        model.generate(torch.tensor([[1]]), temperature=float("nan"))
    with pytest.raises(ValueError, match="temperature"):
        model.generate(torch.tensor([[1]]), temperature=0.001)


def test_causal_attention_does_not_use_future_tokens():
    model = TinyTransformer(TinyTransformerConfig(vocab_size=8, context_length=6, hidden_size=8, num_heads=2))
    model.eval()
    first, _ = model(torch.tensor([[1, 2, 3, 4]]))
    changed, _ = model(torch.tensor([[1, 2, 7, 6]]))
    assert torch.allclose(first[:, :2], changed[:, :2], atol=1e-6)


def test_memory_guard_rejects_over_budget():
    config = TinyTransformerConfig(vocab_size=8, memory_budget_mib=1, reserve_memory_mib=0)
    estimate = estimate_training_memory(config)
    forced = MemoryEstimate(estimate.parameter_count, 2 * 1024 * 1024, 0, 2 * 1024 * 1024, None, 1024 * 1024)
    with pytest.raises(MemoryError, match="exceeds"):
        enforce_memory_budget(config, forced)


@pytest.mark.parametrize("name,optimizer_type", [
    ("adamw", torch.optim.AdamW), ("adam", torch.optim.Adam), ("sgd", torch.optim.SGD),
])
def test_supported_optimizer_selection(name, optimizer_type):
    parameter = torch.nn.Parameter(torch.ones(1))
    assert isinstance(_make_optimizer(name, [parameter], 0.01), optimizer_type)


def test_training_smoke_checkpoint_and_resume(tmp_path):
    source = tmp_path / "lesson.txt"
    source.write_text(("tiny model learns local character patterns.\n" * 40), encoding="utf-8")
    run = tmp_path / "run"
    vocabulary_size = CharacterTokenizer.from_file(source).vocab_size
    torch.manual_seed(17)
    initial = TinyTransformer(TinyTransformerConfig(
        vocab_size=vocabulary_size, context_length=8, hidden_size=8, num_heads=2,
        reserve_memory_mib=0,
    ))
    initial_embedding = initial.token_embedding.weight.detach().clone()
    result = train_tiny_model(
        source, run, context_length=8, hidden_size=8, num_heads=2,
        max_steps=2, checkpoint_interval=1, reserve_memory_mib=0, seed=23,
    )
    assert result["state"] == "COMPLETED"
    assert result["step"] == 2
    assert result["training_loss"] is not None
    assert result["validation_loss"] is not None
    original_job = (run / "job.json").read_text(encoding="utf-8")
    with pytest.raises(FileExistsError, match="fresh run directory"):
        train_tiny_model(source, run, context_length=8, hidden_size=8, num_heads=2, max_steps=2, reserve_memory_mib=0)
    assert (run / "job.json").read_text(encoding="utf-8") == original_job
    checkpoint = result["checkpoints"][-1]
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model = TinyTransformer(TinyTransformerConfig(**state["config"]))
    model.load_state_dict(state["model"])
    assert not torch.equal(initial_embedding, model.token_embedding.weight)
    assert state["step"] == 2
    assert state["config"]["seed"] == 23
    assert state["epoch"] >= 1
    report = evaluate_checkpoint(checkpoint, source, max_batches=2)
    assert report["status"] == "measured"
    assert report["tokens_measured"] > 0
    assert write_evaluation_report(run, report).is_file()
    assert len(generate_text(checkpoint, "tiny", max_new_tokens=2)) == 6
    resumed_run = tmp_path / "resumed-run"
    resumed = train_tiny_model(
        source, resumed_run, context_length=8, hidden_size=8, num_heads=2,
        max_steps=3, reserve_memory_mib=0, resume_from=checkpoint, seed=23,
    )
    assert resumed["state"] == "COMPLETED"
    assert resumed["step"] == 3
    assert resumed["epoch"] >= 1
    registry = ModelRegistry(tmp_path)
    registered = registry.register_completed_run(resumed_run, name="Tiny lesson", dataset_provenance="User-provided test text")
    assert registered["origin"] == "random_initialization"
    assert registered["compatibility_status"].startswith("experimental-only")
    assert all(item["state"] == "COMPLETED" for item in list_experiments(tmp_path))
    registry.select_experimental(registered["model_id"])
    assert registry.active_experimental()["model_id"] == registered["model_id"]
    assert registry.rollback_experimental_selection() is None


def test_training_seed_reproduces_initialization_and_updates(tmp_path):
    source = tmp_path / "repeatable.txt"
    source.write_text("repeatable tiny training example\n" * 20, encoding="utf-8")
    first = train_tiny_model(source, tmp_path / "first", context_length=4, hidden_size=8,
                             num_heads=2, max_steps=1, reserve_memory_mib=0, seed=101)
    second = train_tiny_model(source, tmp_path / "second", context_length=4, hidden_size=8,
                              num_heads=2, max_steps=1, reserve_memory_mib=0, seed=101)
    first_state = torch.load(first["checkpoints"][-1], map_location="cpu", weights_only=True)["model"]
    second_state = torch.load(second["checkpoints"][-1], map_location="cpu", weights_only=True)["model"]
    assert first["training_loss"] == second["training_loss"]
    assert all(torch.equal(first_state[name], second_state[name]) for name in first_state)


def test_pre_cancelled_job_saves_checkpoint(tmp_path):
    source = tmp_path / "lesson.txt"
    source.write_text("small text " * 20, encoding="utf-8")
    cancel = threading.Event()
    cancel.set()
    result = train_tiny_model(
        source, tmp_path / "cancelled", context_length=4, hidden_size=8,
        num_heads=2, reserve_memory_mib=0, cancel_event=cancel,
    )
    assert result["state"] == "CANCELLED"
    assert result["checkpoints"]


def test_failed_training_writes_recoverable_error_state(tmp_path):
    output = tmp_path / "failed"
    with pytest.raises(FileNotFoundError):
        train_tiny_model(tmp_path / "missing.txt", output, reserve_memory_mib=0)
    state = json.loads((output / "job.json").read_text(encoding="utf-8"))
    assert state["state"] == "FAILED"
    assert "dataset file does not exist" in state["error"]
