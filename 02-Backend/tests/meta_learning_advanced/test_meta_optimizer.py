from meta_learning_advanced.meta_optimizer import MetaOptimizer


def test_meta_optimizer_initialization():
    params = {"W": 1.0, "b": 0.0}
    opt = MetaOptimizer(params, lr=0.01)
    assert opt.lr == 0.01
    assert set(opt.params.keys()) == {"W", "b"}
    assert opt.params["W"] == 1.0
    assert opt.state.t == 0


def test_zero_grad():
    params = {"W": 1.0}
    opt = MetaOptimizer(params)
    opt.grads["W"] = 5.0
    opt.zero_grad()
    assert opt.grads["W"] == 0.0


def test_add_grad_and_step():
    params = {"W": 1.0}
    opt = MetaOptimizer(params, lr=0.1)
    opt.zero_grad()
    grads = {"W": 1.0}
    opt.add_grad(grads)
    opt.step()
    assert opt.state.t == 1
    assert opt.params["W"] < params["W"]


def test_step_decreases_loss_direction():
    params = {"W": 1.0}
    opt = MetaOptimizer(params, lr=0.1)
    target = 0.0
    for _ in range(5):
        opt.zero_grad()
        pred = opt.params["W"]
        grad = 2.0 * (pred - target)
        opt.add_grad({"W": grad})
        opt.step()
    final_loss = (opt.params["W"] - target) ** 2
    initial_loss = (params["W"] - target) ** 2
    assert final_loss < initial_loss


def test_state_dict():
    params = {"W": 1.0}
    opt = MetaOptimizer(params)
    opt.zero_grad()
    opt.add_grad({"W": 1.0})
    opt.step()
    state = opt.state_dict()
    assert state["t"] == 1
    assert "W" in state["m"]
    assert "W" in state["v"]


def test_get_params_returns_copies():
    params = {"W": 1.0}
    opt = MetaOptimizer(params)
    returned = opt.get_params()
    returned["W"] = -999.0
    assert opt.params["W"] == 1.0


def test_multiple_steps_tracked():
    params = {"W": 1.0}
    opt = MetaOptimizer(params, lr=0.1)
    for _ in range(3):
        opt.zero_grad()
        opt.add_grad({"W": 1.0})
        opt.step()
    assert opt.state.t == 3
