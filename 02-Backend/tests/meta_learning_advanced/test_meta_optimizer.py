import numpy as np
from meta_learning_advanced.meta_optimizer import MetaOptimizer


def test_meta_optimizer_initialization():
    params = {"W": np.random.randn(4, 3).astype(np.float64), "b": np.zeros(3, dtype=np.float64)}
    opt = MetaOptimizer(params, lr=0.01)
    assert opt.lr == 0.01
    assert set(opt.params.keys()) == {"W", "b"}
    assert opt.params["W"].shape == (4, 3)
    assert opt.state.t == 0


def test_zero_grad():
    params = {"W": np.random.randn(4, 3).astype(np.float64)}
    opt = MetaOptimizer(params)
    opt.grads["W"][:] = 5.0
    opt.zero_grad()
    assert np.allclose(opt.grads["W"], 0.0)


def test_add_grad_and_step():
    np.random.seed(42)
    params = {"W": np.random.randn(4, 3).astype(np.float64)}
    opt = MetaOptimizer(params, lr=0.1)
    opt.zero_grad()
    grads = {"W": np.ones_like(params["W"])}
    opt.add_grad(grads)
    opt.step()
    assert opt.state.t == 1
    assert np.all(opt.params["W"] < params["W"])


def test_step_decreases_loss_direction():
    np.random.seed(0)
    params = {"W": np.random.randn(4, 3).astype(np.float64)}
    opt = MetaOptimizer(params, lr=0.1)
    target = np.ones_like(params["W"])
    for _ in range(5):
        opt.zero_grad()
        pred = opt.params["W"]
        grad = 2.0 * (pred - target) / pred.shape[0]
        opt.add_grad({"W": grad})
        opt.step()
    final_loss = float(np.mean((opt.params["W"] - target) ** 2))
    initial_loss = float(np.mean((params["W"] - target) ** 2))
    assert final_loss < initial_loss


def test_state_dict():
    params = {"W": np.random.randn(2, 2).astype(np.float64)}
    opt = MetaOptimizer(params)
    opt.zero_grad()
    opt.add_grad({"W": np.ones_like(params["W"])})
    opt.step()
    state = opt.state_dict()
    assert state["t"] == 1
    assert "W" in state["m"]
    assert "W" in state["v"]
    assert state["m"]["W"].shape == (2, 2)


def test_get_params_returns_copies():
    params = {"W": np.random.randn(2, 2).astype(np.float64)}
    opt = MetaOptimizer(params)
    returned = opt.get_params()
    returned["W"][0, 0] = -999.0
    assert opt.params["W"][0, 0] != -999.0


def test_multiple_steps_tracked():
    params = {"W": np.random.randn(2, 2).astype(np.float64)}
    opt = MetaOptimizer(params, lr=0.1)
    for _ in range(3):
        opt.zero_grad()
        opt.add_grad({"W": np.ones_like(params["W"])})
        opt.step()
    assert opt.state.t == 3
