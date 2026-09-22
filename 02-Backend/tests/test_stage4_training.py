import pytest
import torch
import torch.nn as nn

from app.core.training import MixedPrecisionTrainer, TrainConfig, AdamW, CosineLRScheduler
from app.core.rlhf import RLHFTrainer, RewardModel, PPOConfig, ppo_loss, compute_advantages, ConstitutionalAI
from app.core.quantization import quantize_weight_int4, dequantize_weight_int4, awq_quantize, gptq_quantize, FakeQuantize, QATTrainer


class TinyModel(nn.Module):
    def __init__(self, vocab_size=100, d_model=32, n_layers=2):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, d_model)
        self.layers = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(n_layers)])
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, x, attention_mask=None):
        h = self.embed(x)
        for layer in self.layers:
            h = layer(h)
        return self.head(h)


def test_adamw_step():
    model = TinyModel()
    optimizer = AdamW(model.parameters(), lr=1e-3)
    x = torch.randint(0, 100, (2, 8))
    y = torch.randint(0, 100, (2, 8))
    logits = model(x)
    loss = nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    assert loss.item() > 0


def test_cosine_lr_scheduler():
    model = TinyModel()
    optimizer = torch.optim.SGD(model.parameters(), lr=1e-3)
    config = TrainConfig(learning_rate=1e-3, warmup_steps=5, max_steps=20)
    scheduler = CosineLRScheduler(optimizer, config)
    initial_lr = optimizer.param_groups[0]["lr"]
    for _ in range(20):
        scheduler.step()
    final_lr = optimizer.param_groups[0]["lr"]
    assert final_lr < initial_lr


def test_mixed_precision_trainer_step():
    model = TinyModel()
    config = TrainConfig(learning_rate=1e-3, use_amp=False)
    trainer = MixedPrecisionTrainer(model, config)
    batch = {
        "input_ids": torch.randint(0, 100, (2, 8)),
        "labels": torch.randint(0, 100, (2, 8)),
    }
    loss = trainer.train_step(batch)
    assert isinstance(loss, float)
    assert loss > 0


def test_compute_advantages():
    rewards = torch.tensor([1.0, 2.0, 3.0])
    values = torch.tensor([0.5, 1.5, 2.5])
    advantages, returns = compute_advantages(rewards, values)
    assert advantages.shape == rewards.shape
    assert returns.shape == rewards.shape


def test_ppo_loss():
    old_log_probs = torch.tensor([-0.5, -0.3])
    new_log_probs = torch.tensor([-0.4, -0.35])
    advantages = torch.tensor([1.0, -1.0])
    config = PPOConfig()
    loss = ppo_loss(old_log_probs, new_log_probs, advantages, config)
    assert loss.shape == ()


def test_reward_model_forward():
    model = TinyModel()
    reward_model = RewardModel(model)
    x = torch.randint(0, 100, (2, 8))
    rewards = reward_model(x)
    assert rewards.shape == (2,)


def test_constitutional_ai_pipeline():
    model = TinyModel()

    class FakeTokenizer:
        def encode(self, text):
            return [1, 2, 3]

    principles = ["Be helpful and harmless"]
    ai = ConstitutionalAI(model, FakeTokenizer(), principles)
    initial, critique, revised = ai.run_pipeline("Hello", "Hi there")
    assert isinstance(initial, str)
    assert isinstance(critique, str)
    assert isinstance(revised, str)


def test_quantize_int4_roundtrip():
    weight = torch.randn(16, 32)
    scale = torch.abs(weight).mean(dim=1, keepdim=True).clamp(min=1e-6)
    q = quantize_weight_int4(weight, scale)
    restored = dequantize_weight_int4(q, scale)
    assert q.shape == weight.shape
    assert restored.shape == weight.shape
    assert restored.dtype == torch.float32


def test_awq_quantize():
    weight = torch.randn(16, 32)
    activation = torch.randn(10, 32)
    q, scale = awq_quantize(weight, activation)
    assert q.shape == weight.shape
    assert scale.shape[0] == weight.shape[0]


def test_gptq_quantize():
    weight = torch.randn(16, 32)
    hessian = torch.randn(32, 32)
    hessian = hessian @ hessian.T + torch.eye(32) * 0.1
    q, scales = gptq_quantize(weight, hessian, blocksize=16)
    assert q.shape == weight.shape
    assert scales.shape[0] == weight.shape[1]


def test_fake_quantize_forward():
    fq = FakeQuantize(n_bits=8)
    x = torch.randn(2, 4)
    out = fq(x)
    assert out.shape == x.shape


def test_qat_trainer_step():
    model = TinyModel()
    config = {"n_bits": 8}
    trainer = QATTrainer(model, config)
    batch = {
        "input_ids": torch.randint(0, 100, (2, 8)),
        "labels": torch.randint(0, 100, (2, 8)),
    }
    loss = trainer.train_step(batch)
    assert isinstance(loss, float)
    assert loss > 0
