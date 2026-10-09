import numpy as np
from training_engine.mixed_precision import MixedPrecisionTrainer


def test_mixed_precision_train_step():
    np.random.seed(0)
    p = np.random.randn(4, 4).astype(np.float32)
    trainer = MixedPrecisionTrainer([p], lr=1e-2, accumulation_steps=1)

    def model_fn(x, params):
        return x @ params[0]

    def loss_fn(logits, y):
        return np.mean((logits - y) ** 2)

    x = np.random.randn(2, 4).astype(np.float32)
    y = np.random.randn(2, 4).astype(np.float32)
    loss = trainer.train_step(x, y, model_fn, loss_fn)
    assert np.isfinite(loss)
    assert not np.allclose(trainer.master_params[0], p)


def test_gradient_accumulation():
    np.random.seed(1)
    p = np.random.randn(4, 4).astype(np.float32)
    trainer = MixedPrecisionTrainer([p], lr=1e-2, accumulation_steps=2)

    def model_fn(x, params):
        return x @ params[0]

    def loss_fn(logits, y):
        return np.mean((logits - y) ** 2)

    x = np.random.randn(2, 4).astype(np.float32)
    y = np.random.randn(2, 4).astype(np.float32)
    loss1 = trainer.train_step(x, y, model_fn, loss_fn)
    loss2 = trainer.train_step(x, y, model_fn, loss_fn)
    assert np.isfinite(loss1)
    assert np.isfinite(loss2)
    assert trainer.step == 2


def test_gradient_clipping_applied():
    np.random.seed(2)
    p = np.random.randn(4, 4).astype(np.float32)
    trainer = MixedPrecisionTrainer([p], lr=1e-2, grad_clip=0.01)

    def model_fn(x, params):
        return x @ params[0]

    def loss_fn(logits, y):
        return np.mean((logits - y) ** 2)

    x = np.random.randn(2, 4).astype(np.float32) * 1e3
    y = np.random.randn(2, 4).astype(np.float32)
    loss = trainer.train_step(x, y, model_fn, loss_fn)
    assert np.isfinite(loss)
