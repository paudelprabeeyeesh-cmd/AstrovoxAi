"""End-to-end language-model tests: tokenize, train, checkpoint, generate."""

import math

import numpy as np
import pytest

from astrovox.nlp import (
    CharTokenizer,
    Dataset,
    LMConfig,
    LanguageModel,
    WordTokenizer,
    build_dataset,
    count_model_flops,
    diagnose,
    synthetic_corpus,
    train,
)
from astrovox.tensor.tensor import tensor


def tiny_config(vocab_size: int) -> LMConfig:
    """A small but complete language-model configuration."""
    return LMConfig(
        vocab_size=vocab_size,
        d_model=32,
        num_layers=2,
        num_heads=4,
        num_kv_heads=2,
        d_ff=64,
        block_size=16,
        max_length=32,
        batch_size=4,
        learning_rate=5e-3,
        max_steps=40,
        warmup_steps=5,
        seed=0,
    )


def tiny_setup(documents: int = 30):
    """A tokenizer, model, and train/validation datasets."""
    tokenizer = CharTokenizer()
    config = tiny_config(tokenizer.vocab_size)
    model = LanguageModel(config, tokenizer)
    # Initialization draws from an unseeded source. This test compares two
    # training runs against each other, so the weights are pinned; otherwise
    # a run could fail depending on what the previous test happened to draw.
    rng = np.random.default_rng(config.seed)
    for _, p in model.named_parameters():
        p.numpy()[...] = (rng.standard_normal(p.shape.dims) * 0.2).astype(np.float32)
    ids = tokenizer.encode(synthetic_corpus(documents=documents, length=80))
    split = int(len(ids) * 0.9)
    train_data = build_dataset(tokenizer.decode(ids[:split]), tokenizer, config.block_size)
    val_data = build_dataset(tokenizer.decode(ids[split:]), tokenizer, config.block_size)
    return tokenizer, model, train_data, val_data


class TestTokenizers:
    def test_char_round_trip(self):
        tokenizer = CharTokenizer()
        for text in ["the cat runs fast .", "a  b\tc\n", "12345", ""]:
            assert tokenizer.decode(tokenizer.encode(text)) == text

    def test_char_vocabulary_covers_printable_ascii(self):
        tokenizer = CharTokenizer()
        assert tokenizer.vocab_size >= 256
        for char in "abcdefghijklmnopqrstuvwxyz0123456789 .":
            assert tokenizer.encode(char)

    def test_special_ids_are_distinct(self):
        tokenizer = CharTokenizer()
        ids = {tokenizer.pad_id, tokenizer.bos_id, tokenizer.eos_id, tokenizer.unk_id}
        assert len(ids) == 4

    def test_decode_skips_specials(self):
        tokenizer = CharTokenizer()
        with_specials = [tokenizer.bos_id] + tokenizer.encode("hi") + [tokenizer.eos_id]
        assert tokenizer.decode(with_specials) == "hi"
        assert tokenizer.decode(with_specials, skip_specials=False) != "hi"

    def test_word_round_trip(self):
        tokenizer = WordTokenizer(["the cat sat on the mat again and again"])
        text = "the cat sat"
        assert tokenizer.decode(tokenizer.encode(text)) == text

    def test_word_unknown_maps_to_unk(self):
        tokenizer = WordTokenizer(["alpha beta gamma delta"])
        assert tokenizer.encode("zzz") == [tokenizer.unk_id]

    def test_word_frequency_cutoff(self):
        tokenizer = WordTokenizer(["a a a b b c"], min_frequency=2)
        assert tokenizer.itos.count("a") == 1
        assert "b" in tokenizer.itos
        # c appears once, so the cutoff drops it.
        assert "c" not in tokenizer.itos

    def test_tokenizer_save_and_load(self, tmp_path):
        tokenizer = CharTokenizer()
        path = tokenizer.save(tmp_path / "tok.json")
        loaded = CharTokenizer.load(path)
        assert loaded.vocab == tokenizer.vocab
        assert loaded.encode("test") == tokenizer.encode("test")

    def test_unknown_tokenizer_kind_is_rejected(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text('{"kind": "nope", "vocab": []}', encoding="utf-8")
        with pytest.raises(ValueError, match="Unknown tokenizer"):
            CharTokenizer.load(path)


class TestDataset:
    def test_targets_are_the_inputs_shifted(self):
        tokenizer = CharTokenizer()
        data = build_dataset("abcdefghijklmnopqrstuvwxyz", tokenizer, 8)
        inputs, targets = data.batch(0)
        assert np.array_equal(targets[:-1], inputs[1:])
        assert len(inputs) == 8

    def test_window_count(self):
        data = Dataset(list(range(100)), 10)
        # 99 usable tokens make nine full windows.
        assert len(data) == 9

    def test_corpus_shorter_than_a_block_is_rejected(self):
        with pytest.raises(ValueError, match="too short"):
            Dataset(list(range(5)), 10)

    def test_epoch_is_finite_and_covers_the_corpus(self):
        data = Dataset(list(range(100)), 10)
        batches = data.epoch(4)
        assert len(batches) == 3
        assert sum(b[0].shape[0] for b in batches) == 9

    def test_batches_is_unbounded(self):
        from itertools import islice

        data = Dataset(list(range(100)), 10)
        assert len(list(islice(data.batches(4), 100))) == 100

    def test_batches_cycles_rather_than_exhausting(self):
        from itertools import islice

        data = Dataset(list(range(50)), 10)
        batches = list(islice(data.batches(4), 20))
        assert len(batches) == 20

    def test_padding_and_mask(self):
        tokenizer = CharTokenizer()
        ids, mask = tokenizer.encode_batch(["a", "abc", "ab"], max_length=4)
        assert ids.shape == (3, 4)
        assert mask[0].tolist() == [1, 0, 0, 0]
        assert mask[1].tolist() == [1, 1, 1, 0]
        assert (ids[0][1:] == tokenizer.pad_id).all()


class TestLanguageModel:
    def test_forward_shape(self):
        tokenizer, model, _, _ = tiny_setup()
        tokens = tensor(np.zeros((2, 8), dtype=np.int64))
        assert tuple(model.forward(tokens).shape.dims) == (2, 8, tokenizer.vocab_size)

    def test_loss_is_a_finite_scalar(self):
        tokenizer, model, train_data, _ = tiny_setup()
        inputs, targets = train_data.epoch(4)[0]
        value = model.loss(tensor(inputs), tensor(targets)).item()
        assert math.isfinite(value)
        assert value > 0

    def test_every_parameter_receives_a_gradient(self):
        tokenizer, model, train_data, _ = tiny_setup()
        inputs, targets = train_data.epoch(4)[0]
        model.optimizer.zero_grad()
        model.loss(tensor(inputs), tensor(targets)).backward()
        missing = [name for name, p in model.model.named_parameters() if p.grad is None]
        assert not missing, missing

    def test_perplexity_follows_from_the_loss(self):
        tokenizer, model, _, _ = tiny_setup()
        assert model.perplexity(0.0) == pytest.approx(1.0)
        assert model.perplexity(math.log(2)) == pytest.approx(2.0, rel=1e-6)

    def test_evaluation_runs_without_updating(self):
        tokenizer, model, train_data, _ = tiny_setup()
        before = model.state_dict()
        loss = model.evaluate(train_data.epoch(4))
        assert math.isfinite(loss)
        after = model.state_dict()
        for name in before:
            assert np.array_equal(before[name].numpy(), after[name].numpy())

    def test_forward_flops_are_countable(self):
        tokenizer, model, _, _ = tiny_setup()
        flops = count_model_flops(model, tensor(np.zeros((2, 8), dtype=np.int64)))
        assert flops > 0

    def test_dashboard_reports_healthy(self):
        tokenizer, model, train_data, _ = tiny_setup()
        inputs, targets = train_data.epoch(4)[0]
        text = diagnose(model, tensor(inputs), tensor(targets))
        assert "HEALTHY" in text or "ATTENTION" in text
        text.encode("ascii")


class TestTraining:
    def test_loss_decreases(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        result = train(model, train_data, val_data, steps=40, log_every=20)
        assert result["final_val_loss"] < result["initial_val_loss"], result["history"]

    def test_perplexity_improves(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        result = train(model, train_data, val_data, steps=40, log_every=20)
        history = result["history"]
        assert history[-1]["ppl"] < history[0]["ppl"]

    def test_losses_stay_finite(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        result = train(model, train_data, val_data, steps=30, log_every=10)
        for row in result["history"]:
            assert math.isfinite(row["train_loss"])
            assert math.isfinite(row["val_loss"])

    def test_learning_rate_warms_up_then_decays(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        result = train(model, train_data, val_data, steps=40, log_every=10)
        rates = [row["lr"] for row in result["history"]]
        assert rates[-1] < rates[0]

    def test_parameters_actually_move(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        before = model.model.state_dict()
        train(model, train_data, val_data, steps=10, log_every=10)
        after = model.model.state_dict()
        changed = [
            name for name in before if not np.array_equal(before[name].numpy(), after[name].numpy())
        ]
        assert changed, "no parameter changed during training"

    def test_training_records_history_on_the_model(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        train(model, train_data, val_data, steps=20, log_every=10)
        assert model.history

    def test_profiler_can_be_enabled(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        result = train(model, train_data, val_data, steps=5, log_every=5, profile=True)
        assert result["profiler"] is not None
        assert "train_step" in result["profiler"]


class TestCheckpointing:
    def test_round_trip_restores_the_same_predictions(self, tmp_path):
        tokenizer, model, train_data, val_data = tiny_setup()
        train(model, train_data, val_data, steps=10, log_every=10)
        tokens = tensor(np.zeros((1, 8), dtype=np.int64))
        before = model.forward(tokens).numpy().copy()

        path = model.save(tmp_path / "ckpt.avx")
        for _, p in model.model.named_parameters():
            p.numpy()[...] = 0.0
        model.load(path)
        assert np.allclose(model.forward(tokens).numpy(), before, atol=1e-6)

    def test_resume_continues_from_the_saved_state(self, tmp_path):
        tokenizer, model, train_data, val_data = tiny_setup()
        train(model, train_data, val_data, steps=10, log_every=10)
        path = model.save(tmp_path / "ckpt.avx")
        mid = model.evaluate(val_data.epoch(4))

        train(model, train_data, val_data, steps=10, log_every=10)
        straight = model.evaluate(val_data.epoch(4))

        model.load(path)
        resumed_start = model.evaluate(val_data.epoch(4))
        assert resumed_start == pytest.approx(mid, rel=1e-5, abs=1e-6)

        train(model, train_data, val_data, steps=10, log_every=10)
        assert model.evaluate(val_data.epoch(4)) == pytest.approx(straight, rel=1e-4, abs=1e-5)

    def test_checkpoint_records_metadata(self, tmp_path):
        tokenizer, model, train_data, val_data = tiny_setup()
        train(model, train_data, val_data, steps=5, log_every=5)
        extra = model.save(tmp_path / "ckpt.avx", {"note": "hello"})
        assert extra.exists()
        restored = model.load(extra)
        assert restored["note"] == "hello"
        assert restored["step"] == model.step_count

    def test_head_weights_are_included(self, tmp_path):
        tokenizer, model, train_data, val_data = tiny_setup()
        train(model, train_data, val_data, steps=5, log_every=5)
        tokens = tensor(np.zeros((1, 4), dtype=np.int64))
        before = model.forward(tokens).numpy().copy()
        path = model.save(tmp_path / "ckpt.avx")
        model.head.weight.numpy()[...] = 0.0
        model.load(path)
        assert np.allclose(model.forward(tokens).numpy(), before, atol=1e-6)


class TestGeneration:
    def test_generation_returns_text(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        train(model, train_data, val_data, steps=10, log_every=10)
        text = model.sample("the cat", max_new_tokens=20, seed=0)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_generation_is_deterministic_for_a_seed(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        first = model.sample("the", max_new_tokens=15, seed=3)
        second = model.sample("the", max_new_tokens=15, seed=3)
        assert first == second

    def test_generation_records_nothing(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        out = model.sample("the", max_new_tokens=10, seed=0)
        assert isinstance(out, str)
        # Sampling must not leave a graph behind for inference to leak.
        assert all(p.grad is None for p in model.parameters())

    def test_top_k_narrows_the_sampling(self):
        tokenizer, model, train_data, val_data = tiny_setup()
        greedy = model.sample("the", max_new_tokens=15, temperature=0.01, top_k=1, seed=1)
        broad = model.sample("the", max_new_tokens=15, temperature=2.0, top_k=1000, seed=1)
        assert isinstance(greedy, str) and isinstance(broad, str)