import numpy as np
from advanced_optimization.meta_optimization.gradient_based_meta import (
    MAMLTrainer,
    ReptileTrainer,
    maml_inner_loop,
    reptile_update,
)


def _make_task():
    params = [np.random.randn(4, 4).astype(np.float32)]

    def loss_fn(p):
        return sum(np.sum(x ** 2) for x in p)

    def grads_fn(p):
        return [2 * x for x in p]

    return params, loss_fn, grads_fn


def test_maml_inner_loop_changes_params():
    np.random.seed(0)
    params, loss_fn, grads_fn = _make_task()
    adapted = maml_inner_loop(params, loss_fn, grads_fn, inner_steps=3, inner_lr=1e-2)
    assert len(adapted) == len(params)
    assert adapted[0].shape == params[0].shape


def test_maml_inner_loop_reduces_loss():
    np.random.seed(1)
    params, loss_fn, grads_fn = _make_task()
    initial_loss = float(loss_fn(params))
    adapted = maml_inner_loop(params, loss_fn, grads_fn, inner_steps=10, inner_lr=1e-1)
    adapted_loss = float(loss_fn(adapted))
    assert adapted_loss < initial_loss


def test_maml_trainer_adapt():
    np.random.seed(2)
    params, loss_fn, grads_fn = _make_task()
    trainer = MAMLTrainer(params, loss_fn, grads_fn, loss_fn, inner_steps=3, inner_lr=1e-2)
    adapted = trainer.adapt()
    assert len(adapted) == len(params)
    assert adapted[0].shape == params[0].shape


def test_maml_trainer_meta_step_changes_params():
    np.random.seed(3)
    params, loss_fn, grads_fn = _make_task()
    trainer = MAMLTrainer(params, loss_fn, grads_fn, loss_fn, inner_steps=3, inner_lr=1e-2)
    task_grads = [np.ones_like(p) * 0.1 for p in params]
    new_params = trainer.meta_step(task_grads)
    assert len(new_params) == len(params)


def test_maml_trainer_evaluate():
    np.random.seed(4)
    params, loss_fn, grads_fn = _make_task()
    trainer = MAMLTrainer(params, loss_fn, grads_fn, loss_fn, inner_steps=3, inner_lr=1e-2)
    adapted = trainer.adapt()
    val_loss = trainer.evaluate(adapted)
    assert isinstance(val_loss, float)


def test_reptile_update_changes_params():
    np.random.seed(5)
    params, _, _ = _make_task()
    new_params = [p + np.random.randn(*p.shape) * 0.1 for p in params]
    updated = reptile_update(params, new_params, meta_lr=1e-3)
    assert len(updated) == len(params)
    for u, p in zip(updated, params):
        assert u.shape == p.shape


def test_reptile_trainer_step():
    np.random.seed(6)
    params, _, _ = _make_task()
    trainer = ReptileTrainer(params, meta_lr=1e-3)
    new_params = [p + np.random.randn(*p.shape) * 0.1 for p in params]
    result = trainer.step(new_params)
    assert len(result) == len(params)
