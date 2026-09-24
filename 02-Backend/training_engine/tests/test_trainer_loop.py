from training_engine.trainer_loop import TrainerLoop, TrainConfig
from training_engine.lr_scheduler import MockOptimizer


def test_trainer_loop_runs():
    model = lambda x: x
    opt = MockOptimizer()
    config = TrainConfig(learning_rate=1e-3, warmup_steps=1, max_steps=5)
    trainer = TrainerLoop(model=model, optimizer=opt, loss_fn=lambda pred, target: 1.0, config=config)
    history = trainer.run()
    assert len(history) == 5


def test_trainer_loop_stops_at_max_steps():
    model = lambda x: x
    opt = MockOptimizer()
    config = TrainConfig(learning_rate=1e-3, warmup_steps=1, max_steps=3)
    trainer = TrainerLoop(model=model, optimizer=opt, loss_fn=lambda pred, target: 1.0, config=config, data=[(None, None)] * 100)
    history = trainer.run()
    assert len(history) == 3


def test_trainer_loop_resume(tmp_path):
    model = lambda x: x
    opt = MockOptimizer()
    config = TrainConfig(learning_rate=1e-3, warmup_steps=1, max_steps=10)
    trainer = TrainerLoop(model=model, optimizer=opt, loss_fn=lambda pred, target: 1.0, config=config, checkpoint_dir=str(tmp_path))
    trainer.run(max_steps=4)
    resumed_step = trainer.resume()
    assert resumed_step == 4
