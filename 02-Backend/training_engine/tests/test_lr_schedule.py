import numpy as np
from training_engine.lr_schedule import CosineLRScheduler


def test_warmup_increases_lr():
    sched = CosineLRScheduler(lr=1e-3, warmup_steps=5, max_steps=20)
    lrs = [sched.step() for _ in range(5)]
    assert np.all(np.diff(lrs) >= 0)


def test_cosine_decay_decreases_lr():
    sched = CosineLRScheduler(lr=1e-3, warmup_steps=5, max_steps=20)
    for _ in range(5):
        sched.step()
    lrs = [sched.step() for _ in range(10)]
    assert lrs[-1] < lrs[0]


def test_deterministic_resumable():
    sched1 = CosineLRScheduler(lr=1e-3, warmup_steps=5, max_steps=20)
    sched2 = CosineLRScheduler(lr=1e-3, warmup_steps=5, max_steps=20)
    for _ in range(10):
        sched1.step()
    for _ in range(10):
        sched2.step()
    assert np.isclose(sched1.get_lr(), sched2.get_lr())
