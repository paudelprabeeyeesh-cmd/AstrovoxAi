"""End-to-end training validation for the neural network library.

The point of these tests is that a deep network trains *every* layer. A
gradient that silently stops partway through still lets the loss fall at first,
so the check that matters is per-layer gradient presence, not the loss curve
alone.
"""

import numpy as np
import pytest

from astrovox import tensor
from astrovox.autograd import backward, check_gradients
from astrovox.nn import (
    GELU,
    LayerNorm,
    Linear,
    ReLU,
    RMSNorm,
    Sequential,
    TransformerBlock,
    TransformerEncoder,
)
from astrovox.ops import cross_entropy, mse_loss
from astrovox.optim import SGD, Adam, AdamW, Lion


def make_binary_dataset(samples: int = 256, features: int = 4, seed: int = 0):
    """Return a linearly separable binary dataset."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((samples, features)).astype(np.float32)
    w = rng.standard_normal(features).astype(np.float32)
    y = (x @ w > 0).astype(np.int64)
    return tensor(x), tensor(y)


#: Each optimizer needs its own learning-rate scale. Lion takes a
#: sign-magnitude step of exactly ``lr``, so it diverges at a rate that is
#: perfectly comfortable for AdamW.
OPTIMIZER_LR = [(SGD, 0.05), (Adam, 0.05), (AdamW, 0.02), (Lion, 0.004)]


def seed_parameters(model, seed: int = 0) -> None:
    """Fill every parameter from a seeded generator.

    Initialization draws from an unseeded source, so without this a
    numerical check would be different on every run and a sporadic failure
    could not be reproduced.
    """
    rng = np.random.default_rng(seed)
    for _, p in model.named_parameters():
        values = rng.standard_normal(p.shape.dims).astype(np.float32)
        p.numpy()[...] = values * 0.5


def mlp(width: int, depth: int, features: int = 4, classes: int = 2, activation=None):
    """Build a plain feed-forward stack of ``depth`` weighted layers."""
    layers = []
    for i in range(depth - 1):
        layers.append(Linear(features if i == 0 else width, width))
        layers.append(activation() if activation else ReLU())
    layers.append(Linear(width, classes))
    return Sequential(*layers)


class TestDeepMLPGradientFlow:
    """Every layer of a deep stack must receive a gradient."""

    @pytest.mark.parametrize("depth", [2, 5, 10, 16])
    def test_every_layer_receives_a_gradient(self, depth):
        model = mlp(width=8, depth=depth)
        x, y = make_binary_dataset(samples=32)
        loss = cross_entropy(model(x), y)
        backward(loss)

        missing = [name for name, p in model.named_parameters() if p.grad is None]
        assert not missing, f"no gradient reached: {missing}"

    @pytest.mark.parametrize("depth", [2, 5, 10, 16])
    def test_no_layer_gradient_is_identically_zero(self, depth):
        """A dead layer is a real failure even though the loss still falls.

        ReLU units can legitimately die, so this uses GELU, which has no
        saturating region that would zero a gradient by construction.
        """
        model = mlp(width=8, depth=depth, activation=GELU)
        x, y = make_binary_dataset(samples=32, seed=3)
        backward(cross_entropy(model(x), y))

        dead = []
        for name, p in model.named_parameters():
            if p.grad is None:
                dead.append(name)
            elif not np.any(p.grad.numpy() != 0.0):
                dead.append(name)
        assert not dead, f"zero gradient on: {dead}"

    def test_gradient_magnitude_decreases_with_depth(self):
        """Deeper layers should not see larger gradients, which would diverge."""
        for depth in (2, 10):
            model = mlp(width=16, depth=depth, activation=GELU)
            x, y = make_binary_dataset(samples=32, seed=5)
            backward(cross_entropy(model(x), y))
            norms = [float((p.grad.numpy() ** 2).sum() ** 0.5) for _, p in model.named_parameters()]
            assert all(np.isfinite(n) for n in norms), f"non-finite gradient at depth {depth}: {norms}"
            assert max(norms) < 1e3, f"gradient too large at depth {depth}: {max(norms):.3g}"


class TestGradientCheckAcrossArchitectures:
    """Numerically verify the gradients of realistic stacks."""

    @pytest.mark.parametrize("depth", [2, 4, 8])
    def test_mlp_gradients_match_numerical(self, depth):
        """Use a smooth activation: finite differences are unreliable at a kink.

        ReLU is checked for gradient *presence* elsewhere; comparing it
        numerically is not meaningful where a pre-activation sits near zero,
        because the finite difference then straddles the corner.
        """
        model = mlp(width=6, depth=depth, activation=GELU)
        seed_parameters(model, seed=17)
        x, y = make_binary_dataset(samples=12, seed=7)
        results = check_gradients(
            lambda: cross_entropy(model(x), y), list(model.parameters()), max_samples=48
        )
        failed = [r for r in results if not r.passed]
        assert not failed, failed[0]

    def test_relu_mlp_gradients_match_away_from_the_kink(self):
        """ReLU checked numerically, with inputs kept clear of the kink."""
        model = mlp(width=6, depth=2)
        seed_parameters(model, seed=19)
        # Every pre-activation is at least 0.5 away from zero, so a central
        # difference never straddles the corner and stays meaningful.
        x = tensor(np.ones((8, 4), dtype=np.float32) * 2.0)
        y = tensor(np.zeros(8, dtype=np.int64))
        results = check_gradients(
            lambda: cross_entropy(model(x), y), list(model.parameters()), max_samples=48
        )
        failed = [r for r in results if not r.passed]
        assert not failed, failed[0]

    def test_layernorm_and_rmsnorm_weights_match_numerical(self):
        for norm_cls in (LayerNorm, RMSNorm):
            for norm in (norm_cls(8),):
                x = tensor(np.random.default_rng(11).standard_normal((6, 8)).astype(np.float32))
                up = tensor(np.random.default_rng(12).standard_normal((6, 8)).astype(np.float32))
                results = check_gradients(
                    lambda: (norm(x) * up).sum(), list(norm.parameters()), max_samples=32
                )
                assert all(r.passed for r in results), f"{norm_cls.__name__}: {results[0]}"

    def test_transformer_block_gradients_match_numerical(self):
        block = TransformerBlock(16, 4, d_ff=32, num_kv_heads=2)
        x = tensor(np.random.default_rng(13).standard_normal((2,5,16)).astype(np.float32))
        up = tensor(np.random.default_rng(14).standard_normal((2,5,16)).astype(np.float32))
        # A loose absolute floor: the loss here is O(10), and a central
        # difference in float32 carries roughly 1e-2/2 of pure rounding noise,
        # which dominates any gradient that is legitimately zero.
        results = check_gradients(
            lambda: (block(x) * up).sum(), list(block.parameters()), max_samples=32, atol=1e-2
        )
        failed = [r for r in results if not r.passed]
        assert not failed, failed[0]

    def test_attention_key_bias_has_no_gradient(self):
        """Softmax is invariant to a per-row shift, so a key bias is unidentifiable.

        The key bias adds ``q . b`` to every score in a row, and softmax
        divides that shift out. Its gradient is therefore exactly zero, not
        approximately zero. Knowing this prevents a future reader from
        treating the zero as a bug or "fixing" it into a wrong nonzero value.
        """
        block = TransformerBlock(16, 4, d_ff=32, num_kv_heads=2)
        x = tensor(np.random.default_rng(17).standard_normal((2, 5, 16)).astype(np.float32))
        up = tensor(np.random.default_rng(18).standard_normal((2, 5, 16)).astype(np.float32))
        backward((block(x) * up).sum())
        key_bias = dict(block.attn.named_parameters())["k_proj.bias"].grad
        assert np.allclose(key_bias.numpy(), 0.0, atol=1e-6), key_bias.numpy()
        # The query and value biases are identifiable and must not be zero.
        for name in ("q_proj.bias", "v_proj.bias"):
            grad = dict(block.attn.named_parameters())[name].grad
            assert np.abs(grad.numpy()).max() > 0.0, f"{name} gradient should be nonzero"

    def test_grouped_query_attention_gradients_match_numerical(self):
        """The head-repeat path needs a node of its own to be differentiable."""
        block = TransformerBlock(16, 8, d_ff=32, num_kv_heads=2)
        x = tensor(np.random.default_rng(15).standard_normal((2, 4, 16)).astype(np.float32))
        up = tensor(np.random.default_rng(16).standard_normal((2, 4, 16)).astype(np.float32))
        results = check_gradients(
            lambda: (block(x) * up).sum(), list(block.parameters()), max_samples=32, atol=1e-2
        )
        assert all(r.passed for r in results), results[0]


class TestTrainingConverges:
    """A model that cannot learn is a broken model."""

    @pytest.mark.parametrize("optimizer_cls,lr", OPTIMIZER_LR)
    def test_reduces_loss_on_a_separable_task(self, optimizer_cls, lr):
        torch_model = mlp(width=16, depth=4)
        x, y = make_binary_dataset(samples=128, features=4, seed=21)
        optimizer = optimizer_cls(list(torch_model.parameters()), lr=lr)

        first = last = None
        for step in range(120):
            optimizer.zero_grad()
            loss = cross_entropy(torch_model(x), y)
            backward(loss)
            optimizer.step()
            if step == 0:
                first = loss.item()
            last = loss.item()
        assert last < first, f"{optimizer_cls.__name__} did not reduce loss: {first:.4f} -> {last:.4f}"

    def test_reaches_high_accuracy_on_a_separable_task(self):
        model = mlp(width=24, depth=3)
        x, y = make_binary_dataset(samples=256, seed=23)
        optimizer = AdamW(list(model.parameters()), lr=0.02)
        for _ in range(300):
            optimizer.zero_grad()
            loss = cross_entropy(model(x), y)
            backward(loss)
            optimizer.step()

        logits = model(x)
        predictions = logits.numpy().argmax(axis=1)
        accuracy = float((predictions == y.numpy()).mean())
        assert accuracy > 0.95, f"accuracy only {accuracy:.3f}"

    def test_ten_layer_mlp_reduces_loss(self):
        """The specific case called out as the acceptance bar for the engine."""
        model = mlp(width=16, depth=10)
        x, y = make_binary_dataset(samples=128, seed=25)
        optimizer = AdamW(list(model.parameters()), lr=0.01)
        history = []
        for _ in range(150):
            optimizer.zero_grad()
            loss = cross_entropy(model(x), y)
            backward(loss)
            optimizer.step()
            history.append(loss.item())
        assert history[-1] < history[0] * 0.7, f"{history[0]:.4f} -> {history[-1]:.4f}"
        assert np.isfinite(history).all()


class TestOptimizerIntegration:
    """Optimizers must actually move parameters in the right direction."""

    @pytest.mark.parametrize("optimizer_cls,lr", OPTIMIZER_LR)
    def test_step_decreases_a_quadratic_loss(self, optimizer_cls, lr):
        model = Sequential(Linear(4, 2))
        x, y = make_binary_dataset(samples=32, seed=27)
        optimizer = optimizer_cls(list(model.parameters()), lr=lr)
        losses = []
        for _ in range(50):
            optimizer.zero_grad()
            loss = cross_entropy(model(x), y)
            backward(loss)
            optimizer.step()
            losses.append(loss.item())
        assert losses[-1] < losses[0], f"{optimizer_cls.__name__}: {losses[0]} -> {losses[-1]}"

    def test_zero_grad_clears_accumulation(self):
        model = Sequential(Linear(4, 2))
        x, y = make_binary_dataset(samples=16, seed=29)
        optimizer = AdamW(list(model.parameters()), lr=0.01)
        optimizer.zero_grad()
        backward(cross_entropy(model(x), y))
        assert any(p.grad is not None for p in model.parameters())
        optimizer.zero_grad()
        assert all(p.grad is None for p in model.parameters())

    def test_gradient_clipping_reduces_the_norm(self):
        model = Sequential(Linear(4, 16), GELU(), Linear(16, 2))
        x, y = make_binary_dataset(samples=16, seed=31)
        optimizer = AdamW(list(model.parameters()), lr=0.0)
        backward(cross_entropy(model(x), y))
        before = optimizer.grad_norm()
        optimizer.clip_grad_norm(0.5)
        assert optimizer.grad_norm() <= before + 1e-6
        assert optimizer.grad_norm() <= 0.5 + 1e-3


class TestModuleSystem:
    """Parameter registration, traversal, and state dicts."""

    def test_named_parameters_are_stable_and_complete(self):
        model = Sequential(Linear(3, 4), GELU(), Linear(4, 2))
        names = [name for name, _ in model.named_parameters()]
        assert names == ["0.weight", "0.bias", "2.weight", "2.bias"]

    def test_state_dict_round_trip_restores_exact_values(self):
        model = Sequential(Linear(3, 4), GELU(), Linear(4, 2))
        x = tensor(np.random.default_rng(33).standard_normal((4, 3)).astype(np.float32))
        before = model(x).numpy().copy()

        target = Sequential(Linear(3, 4), GELU(), Linear(4, 2))
        target.load_state_dict(model.state_dict())
        assert np.array_equal(target(x).numpy(), before)

    def test_state_dict_reports_shape_mismatch(self):
        model = Sequential(Linear(3, 4))
        wrong = {
            "0.weight": tensor(np.zeros((9, 9), dtype=np.float32)),
            "0.bias": tensor(np.zeros(9, dtype=np.float32)),
        }
        with pytest.raises(RuntimeError, match="Shape mismatch"):
            model.load_state_dict(wrong)

    def test_state_dict_reports_missing_keys(self):
        model = Sequential(Linear(3, 4))
        with pytest.raises(RuntimeError, match="Missing keys"):
            model.load_state_dict({"0.weight": tensor(np.zeros((4, 3), dtype=np.float32))})

    def test_parameter_count(self):
        model = mlp(width=6, depth=3, features=3, classes=2)
        # 3->6, 6->6, 6->2
        assert model.num_parameters() == 3 * 6 + 6 + 6 * 6 + 6 + 6 * 2 + 2

    def test_eval_mode_does_not_change_dense_output(self):
        model = Sequential(Linear(3, 2))
        x = tensor(np.random.default_rng(35).standard_normal((4, 3)).astype(np.float32))
        model.train()
        training = model(x).numpy().copy()
        model.eval()
        assert np.array_equal(model(x).numpy(), training)


class TestNumericalStability:
    """Training must not produce non-finite values on ordinary input."""

    def test_large_logits_do_not_produce_nan(self):
        x = tensor(np.array([[100.0, -100.0]], dtype=np.float32))
        model = Sequential(Linear(2, 2))
        for p in model.parameters():
            p.numpy()[...] = p.numpy() * 50.0
        loss = cross_entropy(model(x), tensor(np.array([0])))
        assert np.isfinite(loss.item()), loss.item()

    def test_deep_stack_stays_finite(self):
        model = mlp(width=8, depth=20, activation=GELU)
        x, y = make_binary_dataset(samples=32, seed=37)
        optimizer = AdamW(list(model.parameters()), lr=0.001)
        for _ in range(10):
            optimizer.zero_grad()
            loss = cross_entropy(model(x), y)
            assert np.isfinite(loss.item()), f"non-finite loss at step"
            backward(loss)
            optimizer.step()
        for name, p in model.named_parameters():
            assert np.isfinite(p.numpy()).all(), f"non-finite parameter {name}"


class TestCheckpointResume:
    """Training must be resumable to an identical state."""

    def test_resume_reproduces_the_loss_curve(self, tmp_path):
        from astrovox.tensor.serialization import load_checkpoint, save_checkpoint

        model = mlp(width=8, depth=3)
        x, y = make_binary_dataset(samples=64, seed=39)
        optimizer = AdamW(list(model.parameters()), lr=0.02)

        def run(steps):
            curve = []
            for _ in range(steps):
                optimizer.zero_grad()
                loss = cross_entropy(model(x), y)
                backward(loss)
                optimizer.step()
                curve.append(round(loss.item(), 6))
            return curve

        # state_dict copies, so a later step cannot rewrite the snapshot.
        first_half = run(6)
        path = save_checkpoint(model, tmp_path / "ckpt.avx", {"step": 6})
        opt_state = optimizer.state_dict()
        straight = run(6)

        load_checkpoint(model, path)
        optimizer.load_state_dict(opt_state)
        resumed = run(6)

        assert first_half[0] < 2.0, first_half
        assert straight == pytest.approx(resumed, rel=1e-5, abs=1e-6)
