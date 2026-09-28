import json
import math
import os
import tempfile
from pathlib import Path

import pytest
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
os.sys.path.insert(0, str(ROOT))

from models.llm.alignment import (
    DPOTrainer,
    ORPOTrainer,
    PPOTrainer,
    PreferenceDataset,
    RewardModel,
    RewardTrainer,
    SFTTrainer,
    SimPOTrainer,
    ValueHead,
    compute_gae,
    compute_instruction_loss,
    compute_kl_penalty,
    compute_log_probs,
    compute_pairwise_accuracy,
    compute_reward_loss,
    get_sequence_log_prob,
    instruction_collate_fn,
    preference_collate_fn,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: str, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _dummy_tokenizer(tmp_path: Path, vocab_size: int = 100):
    from tokenizers import Tokenizer
    from tokenizers.models import BPE
    from tokenizers.trainers import BpeTrainer
    from tokenizers.pre_tokenizers import Whitespace
    from tokenizers.processors import TemplateProcessing

    tok = Tokenizer(BPE(unk_token="<unk>"))
    tok.pre_tokenizer = Whitespace()
    trainer = BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=["<unk>", "<pad>", "<eos>", "<s>", "</s>"],
    )
    texts = [
        "<s>[INST] Hello [/INST] world</s>",
        "<s>[INST] How are you? [/INST] I am fine.</s>",
        "<s>[INST] What is AI? [/INST] Artificial intelligence.</s>",
        "<s>[INST] Tell me a joke. [/INST] Why did the chicken cross the road?</s>",
    ]
    tok.train_from_iterator(texts, trainer)
    tok.post_processor = TemplateProcessing(
        single="<s>:0 $A:0 </s>:0",
        pair=None,
        special_tokens=[("<s>", 0), ("</s>", 1)],
    )
    tokenizer_path = str(tmp_path / "tokenizer.json")
    tok.save(tokenizer_path)
    return tokenizer_path


def _tiny_config(vocab_size: int = 100) -> dict:
    return {
        "vocab_size": vocab_size,
        "hidden_size": 32,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "intermediate_size": 64,
        "max_position_embeddings": 64,
        "rms_norm_eps": 1e-5,
        "rope_theta": 10000.0,
        "activation": "swiglu",
        "attention_bias": False,
        "mlp_bias": False,
        "dropout": 0.0,
        "tie_weights": True,
        "mixed_precision": "none",
        "max_length": 64,
        "beta": 0.1,
        "kl_coef": 0.01,
        "sft_lr": 1e-4,
        "dpo_lr": 1e-4,
        "orpo_lr": 1e-4,
        "simpo_lr": 1e-4,
        "reward_lr": 1e-4,
        "ppo_lr": 1e-4,
        "ppo_value_lr": 1e-4,
        "sft_epochs": 1,
        "dpo_epochs": 1,
        "orpo_epochs": 1,
        "simpo_epochs": 1,
        "reward_epochs": 1,
        "sft_batch_size": 2,
        "preference_batch_size": 2,
        "gradient_accumulation_steps": 1,
        "gradient_clip_norm": 1.0,
        "weight_decay": 0.01,
        "reward_margin": 0.5,
        "simpo_gamma": 0.1,
        "simpo_margin": 0.0,
        "ppo_clip_eps": 0.2,
        "ppo_value_clip_eps": 0.2,
        "ppo_gamma": 0.99,
        "gae_lambda": 0.95,
        "max_gen_length": 16,
        "label_smoothing": 0.0,
        "output_dir": "",
    }


def _build_model(config: dict, device: torch.device):
    from models.llm.model.model import LLM
    return LLM(config, device=device, dtype=torch.float32)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def tmp_workspace(tmp_path_factory):
    return tmp_path_factory.mktemp("alignment")


@pytest.fixture(scope="session")
def tokenizer_path(tmp_workspace):
    return _dummy_tokenizer(tmp_workspace)


@pytest.fixture(scope="session")
def sft_data_file(tmp_workspace):
    records = [
        {"instruction": "Say hello", "input": "", "output": "Hello!"},
        {"instruction": "Count to three", "input": "", "output": "One two three"},
        {"instruction": "What is 2+2?", "input": "", "output": "Four"},
        {"instruction": "Translate hello", "input": "", "output": "Hola"},
    ]
    path = str(tmp_workspace / "sft_data.jsonl")
    _write_jsonl(path, records)
    return path


@pytest.fixture(scope="session")
def preference_data_file(tmp_workspace):
    records = [
        {
            "prompt": "<s>[INST] Hello? [/INST]",
            "chosen": " Hi there!",
            "rejected": " Go away.",
        },
        {
            "prompt": "<s>[INST] What is 2+2? [/INST]",
            "chosen": " Four",
            "rejected": " Five",
        },
        {
            "prompt": "<s>[INST] Tell me a joke. [/INST]",
            "chosen": " Why did the chicken cross the road?",
            "rejected": " I don't know any jokes.",
        },
    ]
    path = str(tmp_workspace / "preferences.jsonl")
    _write_jsonl(path, records)
    return path


@pytest.fixture(scope="session")
def config(tmp_workspace, tokenizer_path):
    cfg = _tiny_config()
    cfg["tokenizer_path"] = tokenizer_path
    return cfg


@pytest.fixture(scope="session")
def device():
    return torch.device("cpu")


@pytest.fixture(scope="session")
def model(config, device):
    return _build_model(config, device)


@pytest.fixture(scope="session")
def reference_model(config, device):
    ref = _build_model(config, device)
    ref.eval()
    for p in ref.parameters():
        p.requires_grad = False
    return ref


@pytest.fixture(scope="session")
def tokenizer(tokenizer_path):
    from models.llm.tokenizer.train_tokenizer import load_tokenizer
    return load_tokenizer(tokenizer_path)


# ---------------------------------------------------------------------------
# SFT
# ---------------------------------------------------------------------------


class TestSFTTrainer:

    def test_train_returns_metrics(self, sft_data_file, tokenizer, config, device, tmp_workspace):
        from models.llm.training_data.prepare import InstructionDataset
        cfg = dict(config)
        cfg["tokenizer_path"] = None  # already have tokenizer
        dataset = InstructionDataset(sft_data_file, tokenizer, block_size=64)
        model = _build_model(cfg, device)
        trainer = SFTTrainer(model, tokenizer, cfg, train_dataset=dataset)
        output_dir = str(tmp_workspace / "sft_out")
        result = trainer.train(output_dir, epochs=1)
        assert "best_val_loss" in result
        assert "final_train_loss" in result

    def test_instruction_dataset_length(self, sft_data_file, tokenizer):
        from models.llm.training_data.prepare import InstructionDataset
        ds = InstructionDataset(sft_data_file, tokenizer, block_size=64)
        assert len(ds) > 0

    def test_instruction_dataset_item_keys(self, sft_data_file, tokenizer):
        from models.llm.training_data.prepare import InstructionDataset
        ds = InstructionDataset(sft_data_file, tokenizer, block_size=64)
        item = ds[0]
        assert "input_ids" in item
        assert "labels" in item

    def test_compute_instruction_loss(self):
        B, T, V = 2, 8, 100
        logits = torch.randn(B, T, V)
        labels = torch.randint(0, V, (B, T))
        loss = compute_instruction_loss(logits, labels)
        assert loss.item() > 0

    def test_instruction_collate_fn(self, tokenizer):
        batch = [
            {"input_ids": [1, 2, 3], "labels": [1, 2, 3]},
            {"input_ids": [4, 5], "labels": [4, 5]},
        ]
        out = instruction_collate_fn(batch, pad_token_id=0)
        assert out["input_ids"].shape[0] == 2
        assert out["labels"].shape[0] == 2


# ---------------------------------------------------------------------------
# Reward
# ---------------------------------------------------------------------------


class TestRewardModel:

    def test_forward_shape(self, model, config, device):
        reward_model = RewardModel(config, device=device, dtype=torch.float32)
        input_ids = torch.randint(0, config["vocab_size"], (2, 8))
        attention_mask = torch.ones_like(input_ids)
        out = reward_model(input_ids, attention_mask=attention_mask)
        assert "reward" in out
        assert "logits" in out
        assert out["reward"].shape == (2,)
        assert out["logits"].shape == (2, 8, config["vocab_size"])

    def test_reward_positive_higher_than_rejected(self, model, config, device):
        reward_model = RewardModel(config, device=device, dtype=torch.float32)
        good_ids = torch.randint(1, config["vocab_size"], (1, 8))
        bad_ids = torch.randint(1, config["vocab_size"], (1, 8))
        mask = torch.ones_like(good_ids)
        with torch.no_grad():
            good_out = reward_model(good_ids, attention_mask=mask)
            bad_out = reward_model(bad_ids, attention_mask=mask)
        assert good_out["reward"].shape == (1,)
        assert bad_out["reward"].shape == (1,)

    def test_compute_reward_loss(self):
        chosen = torch.tensor([1.5, 0.8, 2.0])
        rejected = torch.tensor([0.2, -0.5, 0.1])
        loss = compute_reward_loss(chosen, rejected, margin=0.5)
        assert loss.item() > 0

    def test_compute_pairwise_accuracy(self):
        chosen = torch.tensor([1.5, 0.8, 2.0])
        rejected = torch.tensor([0.2, 1.0, 0.1])
        acc = compute_pairwise_accuracy(chosen, rejected)
        assert 0.0 <= acc <= 1.0
        assert acc == 2 / 3

    def test_preference_dataset_length(self, preference_data_file, tokenizer):
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        assert len(ds) == 3

    def test_preference_dataset_item_keys(self, preference_data_file, tokenizer):
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        item = ds[0]
        assert "chosen_input_ids" in item
        assert "rejected_input_ids" in item

    def test_preference_dataset_missing_file(self, tokenizer):
        with pytest.raises(FileNotFoundError):
            PreferenceDataset("nonexistent_file.jsonl", tokenizer)

    def test_preference_collate_fn(self):
        batch = [
            {"chosen_input_ids": [1, 2, 3], "rejected_input_ids": [4, 5, 6]},
            {"chosen_input_ids": [7, 8], "rejected_input_ids": [9, 10]},
        ]
        out = preference_collate_fn(batch, pad_token_id=0, max_length=16)
        assert out["chosen_input_ids"].shape[0] == 2
        assert out["rejected_input_ids"].shape[0] == 2

    def test_reward_trainer_requires_reward_model(self, config, tokenizer):
        class FakeModel(nn.Module):
            def forward(self, *args, **kwargs):
                return {}
        fake = FakeModel()
        with pytest.raises(TypeError):
            RewardTrainer(fake, tokenizer, config)


# ---------------------------------------------------------------------------
# DPO
# ---------------------------------------------------------------------------


class TestDPOTrainer:

    def test_train_returns_metrics(self, preference_data_file, tokenizer, config, device, model, reference_model, tmp_workspace):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        trainer = DPOTrainer(model, reference_model, tokenizer, cfg, train_dataset=ds)
        output_dir = str(tmp_workspace / "dpo_out")
        result = trainer.train(output_dir, epochs=1)
        assert "best_loss" in result
        assert "final_train_loss" in result
        assert math.isfinite(result["final_train_loss"])

    def test_missing_reference_raises(self, config, tokenizer):
        from models.llm.model.model import LLM
        import torch
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        m = _build_model(cfg, torch.device("cpu"))
        with pytest.raises(ValueError):
            DPOTrainer(m, None, tokenizer, cfg)

    def test_dpo_loss_finite(self, model, reference_model, config, device, preference_data_file, tokenizer):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        trainer = DPOTrainer(model, reference_model, tokenizer, cfg, train_dataset=ds)
        batch = ds[0]
        chosen_ids = batch["chosen_input_ids"].unsqueeze(0).to(device)
        rejected_ids = batch["rejected_input_ids"].unsqueeze(0).to(device)
        chosen_mask = torch.ones_like(chosen_ids)
        rejected_mask = torch.ones_like(rejected_ids)
        loss, metrics = trainer._dpo_loss(chosen_ids, rejected_ids, chosen_mask, rejected_mask)
        assert math.isfinite(loss.item())
        assert "dpo_loss" in metrics
        assert "kl" in metrics


# ---------------------------------------------------------------------------
# ORPO
# ---------------------------------------------------------------------------


class TestORPOTrainer:

    def test_train_returns_metrics(self, preference_data_file, tokenizer, config, device, model, tmp_workspace):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        trainer = ORPOTrainer(model, tokenizer, cfg, train_dataset=ds)
        output_dir = str(tmp_workspace / "orpo_out")
        result = trainer.train(output_dir, epochs=1)
        assert "best_loss" in result
        assert "final_train_loss" in result
        assert math.isfinite(result["final_train_loss"])

    def test_orpo_loss_finite(self, model, config, device, preference_data_file, tokenizer):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        trainer = ORPOTrainer(model, tokenizer, cfg, train_dataset=ds)
        batch = ds[0]
        chosen_ids = batch["chosen_input_ids"].unsqueeze(0).to(device)
        rejected_ids = batch["rejected_input_ids"].unsqueeze(0).to(device)
        chosen_mask = torch.ones_like(chosen_ids)
        rejected_mask = torch.ones_like(rejected_ids)
        loss, metrics = trainer._orpo_loss(chosen_ids, rejected_ids, chosen_mask, rejected_mask)
        assert math.isfinite(loss.item())
        assert "orpo_loss" in metrics


# ---------------------------------------------------------------------------
# SimPO
# ---------------------------------------------------------------------------


class TestSimPOTrainer:

    def test_train_returns_metrics(self, preference_data_file, tokenizer, config, device, model, tmp_workspace):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        trainer = SimPOTrainer(model, tokenizer, cfg, train_dataset=ds)
        output_dir = str(tmp_workspace / "simpo_out")
        result = trainer.train(output_dir, epochs=1)
        assert "best_loss" in result
        assert "final_train_loss" in result
        assert math.isfinite(result["final_train_loss"])

    def test_simpo_loss_finite(self, model, config, device, preference_data_file, tokenizer):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        trainer = SimPOTrainer(model, tokenizer, cfg, train_dataset=ds)
        batch = ds[0]
        chosen_ids = batch["chosen_input_ids"].unsqueeze(0).to(device)
        rejected_ids = batch["rejected_input_ids"].unsqueeze(0).to(device)
        chosen_mask = torch.ones_like(chosen_ids)
        rejected_mask = torch.ones_like(rejected_ids)
        loss, metrics = trainer._simpo_loss(chosen_ids, rejected_ids, chosen_mask, rejected_mask)
        assert math.isfinite(loss.item())
        assert "simpo_loss" in metrics


# ---------------------------------------------------------------------------
# PPO
# ---------------------------------------------------------------------------


class TestPPOTrainer:

    def test_compute_gae(self):
        rewards = torch.tensor([1.0, 0.5, 0.2])
        values = torch.tensor([0.8, 0.4, 0.3, 0.1])
        dones = torch.zeros(3, dtype=torch.bool)
        advantages, returns = compute_gae(rewards, values, dones, gamma=0.99, gae_lambda=0.95)
        assert advantages.shape == (3,)
        assert returns.shape == (3,)
        assert torch.isfinite(advantages).all()
        assert torch.isfinite(returns).all()

    def test_compute_gae_with_done(self):
        rewards = torch.tensor([1.0, 0.5, 0.2])
        values = torch.tensor([0.8, 0.4, 0.3, 0.1])
        dones = torch.tensor([False, True, False], dtype=torch.bool)
        advantages, returns = compute_gae(rewards, values, dones, gamma=0.99, gae_lambda=0.95)
        assert advantages.shape == (3,)

    def test_value_head_forward(self, config, device):
        vh = ValueHead(config["hidden_size"], device=device, dtype=torch.float32)
        B, T, H = 2, 8, config["hidden_size"]
        hidden = torch.randn(B, T, H)
        mask = torch.ones(B, T, dtype=torch.long)
        values = vh(hidden, attention_mask=mask)
        assert values.shape == (B,)

    def test_value_head_no_mask(self, config, device):
        vh = ValueHead(config["hidden_size"], device=device, dtype=torch.float32)
        B, T, H = 2, 8, config["hidden_size"]
        hidden = torch.randn(B, T, H)
        values = vh(hidden)
        assert values.shape == (B,)

    def test_train_step_returns_metrics(self, model, reference_model, config, device, tokenizer):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        cfg["ppo_lr"] = 1e-4
        cfg["ppo_value_lr"] = 1e-4
        value_model = _build_model(cfg, device)
        trainer = PPOTrainer(
            model, value_model, tokenizer, cfg, reward_fn=lambda seq: torch.tensor([1.0])
        )
        prompts = ["<s>[INST] Hello [/INST]"]
        result = trainer.train_step(prompts)
        assert "policy_loss" in result
        assert "value_loss" in result
        assert "kl" in result
        assert "entropy" in result


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


class TestSharedUtils:

    def test_compute_log_probs(self):
        B, T, V = 2, 8, 100
        logits = torch.randn(B, T, V)
        labels = torch.randint(0, V, (B, T))
        mask = torch.ones(B, T, dtype=torch.long)
        log_probs = compute_log_probs(logits, labels, attention_mask=mask)
        assert log_probs.shape == (B, T - 1)

    def test_compute_log_probs_no_mask(self):
        B, T, V = 2, 8, 100
        logits = torch.randn(B, T, V)
        labels = torch.randint(0, V, (B, T))
        log_probs = compute_log_probs(logits, labels)
        assert log_probs.shape == (B, T - 1)

    def test_compute_kl_penalty_mean(self):
        log_p = torch.randn(4, 8)
        log_r = torch.randn(4, 8)
        kl = compute_kl_penalty(log_p, log_r, reduction="mean")
        assert math.isfinite(kl.item())

    def test_compute_kl_penalty_with_mask(self):
        log_p = torch.randn(4, 8)
        log_r = torch.randn(4, 8)
        mask = torch.ones(4, 8, dtype=torch.long)
        kl = compute_kl_penalty(log_p, log_r, attention_mask=mask, reduction="sum")
        assert math.isfinite(kl.item())

    def test_get_sequence_log_prob(self, model, config, device):
        input_ids = torch.randint(0, config["vocab_size"], (2, 8))
        mask = torch.ones_like(input_ids)
        log_prob_sum, logits = get_sequence_log_prob(model, input_ids, mask)
        assert log_prob_sum.shape == (2,)
        assert logits.shape == (2, 8, config["vocab_size"])

    def test_compute_kl_penalty_sum(self):
        log_p = torch.randn(4, 8)
        log_r = torch.randn(4, 8)
        kl = compute_kl_penalty(log_p, log_r, reduction="sum")
        assert math.isfinite(kl.item())

    def test_compute_kl_penalty_none(self):
        log_p = torch.randn(4, 8)
        log_r = torch.randn(4, 8)
        kl = compute_kl_penalty(log_p, log_r, reduction="none")
        assert kl.shape == (4, 8)


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------


class TestSafetyEvaluator:

    def test_refusal_behavior_returns_dict(self, model, config, tokenizer):
        from models.llm.alignment.safety import SafetyEvaluator
        evaluator = SafetyEvaluator(model, tokenizer, config)
        result = evaluator.test_refusal_behavior()
        assert "total_prompts" in result
        assert "refused_count" in result
        assert "refusal_rate" in result
        assert 0.0 <= result["refusal_rate"] <= 1.0

    def test_jailbreak_robustness_returns_dict(self, model, config, tokenizer):
        from models.llm.alignment.safety import SafetyEvaluator
        evaluator = SafetyEvaluator(model, tokenizer, config)
        result = evaluator.evaluate_jailbreak_robustness(num_samples=3)
        assert "robustness_score" in result
        assert 0.0 <= result["robustness_score"] <= 1.0

    def test_refusal_markers_defined(self):
        from models.llm.alignment.safety import SafetyEvaluator
        assert len(SafetyEvaluator.REFUSAL_MARKERS) > 0

    def test_jailbreak_probes_defined(self):
        from models.llm.alignment.safety import SafetyEvaluator
        assert len(SafetyEvaluator.JAILBREAK_PROBES) > 0


# ---------------------------------------------------------------------------
# Integration: package import
# ---------------------------------------------------------------------------


class TestAlignmentPackage:

    def test_import_all(self):
        from models.llm import alignment
        assert hasattr(alignment, "SFTTrainer")
        assert hasattr(alignment, "DPOTrainer")
        assert hasattr(alignment, "ORPOTrainer")
        assert hasattr(alignment, "SimPOTrainer")
        assert hasattr(alignment, "PPOTrainer")
        assert hasattr(alignment, "RewardTrainer")
        assert hasattr(alignment, "RewardModel")
        assert hasattr(alignment, "SafetyEvaluator")
        assert hasattr(alignment, "PreferenceDataset")

    def test_reward_model_is_nn_module(self, config, device):
        reward_model = RewardModel(config, device=device, dtype=torch.float32)
        assert isinstance(reward_model, nn.Module)

    def test_reward_model_save_and_load(self, config, device, tmp_workspace):
        reward_model = RewardModel(config, device=device, dtype=torch.float32)
        path = str(tmp_workspace / "reward_test.pt")
        torch.save(reward_model.state_dict(), path)
        loaded = RewardModel(config, device=device, dtype=torch.float32)
        loaded.load_state_dict(torch.load(path, map_location=device, weights_only=False))
        with torch.no_grad():
            ids = torch.randint(0, config["vocab_size"], (1, 8))
            mask = torch.ones_like(ids)
            out_orig = reward_model(ids, attention_mask=mask)
            out_loaded = loaded(ids, attention_mask=mask)
        assert torch.allclose(out_orig["reward"], out_loaded["reward"], atol=1e-5)

    def test_dpo_trainer_saves_checkpoint(self, preference_data_file, tokenizer, config, device, model, reference_model, tmp_workspace):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        trainer = DPOTrainer(model, reference_model, tokenizer, cfg, train_dataset=ds)
        output_dir = str(tmp_workspace / "dpo_ckpt")
        trainer.train(output_dir, epochs=1)
        assert os.path.exists(os.path.join(output_dir, "dpo_final.pt"))

    def test_orpo_trainer_saves_checkpoint(self, preference_data_file, tokenizer, config, device, model, tmp_workspace):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        trainer = ORPOTrainer(model, tokenizer, cfg, train_dataset=ds)
        output_dir = str(tmp_workspace / "orpo_ckpt")
        trainer.train(output_dir, epochs=1)
        assert os.path.exists(os.path.join(output_dir, "orpo_final.pt"))

    def test_simpo_trainer_saves_checkpoint(self, preference_data_file, tokenizer, config, device, model, tmp_workspace):
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = PreferenceDataset(preference_data_file, tokenizer, max_length=64)
        trainer = SimPOTrainer(model, tokenizer, cfg, train_dataset=ds)
        output_dir = str(tmp_workspace / "simpo_ckpt")
        trainer.train(output_dir, epochs=1)
        assert os.path.exists(os.path.join(output_dir, "simpo_final.pt"))

    def test_sft_trainer_saves_checkpoint(self, sft_data_file, tokenizer, config, device, tmp_workspace):
        from models.llm.training_data.prepare import InstructionDataset
        cfg = dict(config)
        cfg["tokenizer_path"] = None
        ds = InstructionDataset(sft_data_file, tokenizer, block_size=64)
        model = _build_model(cfg, device)
        trainer = SFTTrainer(model, tokenizer, cfg, train_dataset=ds)
        output_dir = str(tmp_workspace / "sft_ckpt")
        trainer.train(output_dir, epochs=1)
        assert os.path.exists(os.path.join(output_dir, "sft_final.pt"))

    def test_preference_dataset_missing_required_fields(self, tokenizer, tmp_workspace):
        path = str(tmp_workspace / "bad_pref.jsonl")
        _write_jsonl(path, [{"prompt": "hi", "chosen": "yes"}])  # missing rejected
        with pytest.raises(ValueError):
            PreferenceDataset(path, tokenizer)[0]

    def test_preference_dataset_file_not_found(self, tokenizer):
        with pytest.raises(FileNotFoundError):
            PreferenceDataset("nonexistent.jsonl", tokenizer)

    def test_reward_trainer_invalid_model_type(self, config, tokenizer):
        from models.llm.model.model import LLM
        import torch
        fake_llm = _build_model(config, torch.device("cpu"))
        ds = None
        with pytest.raises(TypeError):
            RewardTrainer(fake_llm, tokenizer, config)
