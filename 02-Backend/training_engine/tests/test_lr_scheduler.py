import math

from training_engine.lr_scheduler import LRScheduler, MockOptimizer, TrainConfig


def test_initial_lr_after_warmup():
    opt = MockOptimizer()
    config = TrainConfig(learning_rate=1e-3, warmup_steps=5, max_steps=20)
    sched = LRScheduler(opt, config)
    lr = sched.get_lr()
    assert math.isclose(lr, 1e-3)


def test_warmup_increases_lr():
    opt = MockOptimizer()
    sched = LRScheduler(opt, TrainConfig(learning_rate=1e-3, warmup_steps=5, max_steps=20))
    lrs = [sched.step() for _ in range(5)]
    assert all(lrs[i] <= lrs[i + 1] for i in range(len(lrs) - 1))


def test_cosine_decay_decreases_lr():
    opt = MockOptimizer()
    sched = LRScheduler(opt, TrainConfig(learning_rate=1e-3, warmup_steps=5, max_steps=20))
    for _ in range(5):
        sched.step()
    lrs = [sched.step() for _ in range(10)]
    assert lrs[-1] < lrs[0]


def test_min_lr_floor():
    opt = MockOptimizer()
    config = TrainConfig(learning_rate=1e-3, warmup_steps=1, max_steps=2, min_lr=1e-6)
    sched = LRScheduler(opt, config)
    for _ in range(100):
        sched.step()
    assert sched.get_lr() >= config.min_lr - 1e-12


def test_step_updates_optimizer_lr():
    opt = MockOptimizer()
    config = TrainConfig(learning_rate=0.5, warmup_steps=1, max_steps=2)
    sched = LRScheduler(opt, config)
    sched.step()
    assert math.isclose(opt.lr, 0.5)
