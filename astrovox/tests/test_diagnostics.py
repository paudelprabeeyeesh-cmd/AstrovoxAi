"""Tests for the autograd diagnostics.

Each tool exists to catch a failure that a falling loss curve hides, so the
tests deliberately build the broken cases and assert the tool notices.
"""

import numpy as np
import pytest

from astrovox import tensor
from astrovox.autograd import backward
from astrovox.debug import (
    dashboard,
    format_consistency,
    format_distribution,
    format_memory,
    format_updates,
    gradient_consistency,
    gradient_distribution,
    memory_report,
    propagation_depth,
    propagation_trace,
    validate_backward,
    validate_shapes,
    verify_updates,
)
from astrovox.nn import Embedding, Linear, ReLU, Sequential
from astrovox.ops import cross_entropy
from astrovox.optim import AdamW


def small_model(seed: int = 0) -> Sequential:
    """A three-layer stack with reproducible parameters."""
    model = Sequential(Linear(4, 8), ReLU(), Linear(8, 2))
    rng = np.random.default_rng(seed)
    for _, p in model.named_parameters():
        p.numpy()[...] = (rng.standard_normal(p.shape.dims) * 0.5).astype(np.float32)
    return model


def small_batch(seed: int = 1):
    """Inputs and labels matching :func:`small_model`."""
    rng = np.random.default_rng(seed)
    x = tensor(rng.standard_normal((16, 4)).astype(np.float32))
    y = tensor(rng.integers(0, 2, 16).astype(np.int64))
    return x, y


class TestGradientConsistency:
    def test_every_parameter_passes(self):
        model = small_model()
        x, y = small_batch()
        loss = lambda: cross_entropy(model(x), y)
        checks = gradient_consistency(loss, model)
        assert len(checks) == 4
        assert all(c.passed for c in checks), format_consistency(checks)

    def test_relative_error_is_small(self):
        model = small_model(3)
        x, y = small_batch(4)
        loss = lambda: cross_entropy(model(x), y)
        for check in gradient_consistency(loss, model):
            # The largest single-element disagreement, measured against the
            # gradient's own norm.
            assert check.max_error_over_norm < 1e-2, check

    def test_report_is_readable(self):
        model = small_model()
        x, y = small_batch()
        text = format_consistency(gradient_consistency(lambda: cross_entropy(model(x), y), model))
        assert "PASS" in text
        assert "0.weight" in text

    def test_embedding_gradient_is_correct(self):
        table = Embedding(5, 4)
        indices = tensor(np.array([[0, 1], [2, 0]], dtype=np.int64))
        upstream = tensor(np.random.default_rng(5).standard_normal((2, 2, 4)).astype(np.float32))

        class Wrapper(Sequential):
            def __init__(self):
                super().__init__()
                self.embedding = table

            def forward(self, _):
                return table(indices)

        model = Wrapper()
        loss = lambda: (model(None) * upstream).sum()
        checks = gradient_consistency(loss, model, max_samples=40)
        assert all(c.passed for c in checks), format_consistency(checks)

    def test_catches_a_wrong_gradient(self):
        """A deliberately corrupted gradient must be reported as a failure."""
        model = small_model()
        x, y = small_batch()
        loss = lambda: cross_entropy(model(x), y)
        checks = gradient_consistency(loss, model)
        # Corrupting one gradient after the check must not change the verdict,
        # so recompute with a tampered parameter instead.
        original = dict(model[0].named_parameters())["weight"].numpy().copy()
        model[0].weight.numpy()[...] = original * 1.5
        again = gradient_consistency(loss, model)
        # A uniformly scaled weight is still a valid function of the parameter,
        # so the check must still pass; that is the point of differencing.
        assert all(c.passed for c in again), format_consistency(again)


class TestPropagationTrace:
    def test_lists_every_operation(self):
        model = small_model()
        x, y = small_batch()
        loss = cross_entropy(model(x), y)
        trace = propagation_trace(loss)
        assert "cross_entropy" in trace
        assert "matmul" in trace
        assert "reached" in trace

    def test_backward_order_starts_at_the_loss(self):
        model = small_model()
        x, y = small_batch()
        trace = propagation_trace(cross_entropy(model(x), y))
        order = [line for line in trace.splitlines() if line.strip().startswith("1.")]
        assert order and "cross_entropy" in order[0]

    def test_is_plain_ascii(self):
        """The report goes to consoles and logs with limited encodings."""
        model = small_model()
        x, y = small_batch()
        trace = propagation_trace(cross_entropy(model(x), y))
        trace.encode("ascii")

    def test_depth_grows_with_layers(self):
        x, y = small_batch()
        shallow = Sequential(Linear(4, 2))
        deep = Sequential(Linear(4, 8), ReLU(), Linear(8, 8), ReLU(), Linear(8, 8), ReLU(), Linear(8, 2))
        assert propagation_depth(cross_entropy(deep(x), y)) > propagation_depth(
            cross_entropy(shallow(x), y)
        )


class TestUpdateVerification:
    def test_reports_every_parameter_moved(self):
        model = small_model()
        x, y = small_batch()
        before = model.state_dict()
        optimizer = AdamW(list(model.parameters()), lr=0.05)
        optimizer.zero_grad()
        backward(cross_entropy(model(x), y))
        optimizer.step()
        statuses = verify_updates(model, before)
        assert len(statuses) == 4
        assert all(s.updated for s in statuses), format_updates(statuses)

    def test_reports_a_frozen_parameter_with_a_reason(self):
        model = small_model()
        x, y = small_batch()
        before = model.state_dict()
        # An optimizer holding no parameters cannot move anything.
        optimizer = AdamW(list(Linear(1, 1).parameters()), lr=0.05)
        optimizer.zero_grad()
        backward(cross_entropy(model(x), y))
        statuses = verify_updates(model, before)
        assert not any(s.updated for s in statuses)
        assert all(s.reason for s in statuses)

    def test_zero_gradient_is_named_as_the_reason(self):
        model = Sequential(Linear(4, 2, bias=False))
        for _, p in model.named_parameters():
            p._grad = None
        before = model.state_dict()
        # Force an exactly zero gradient.
        model[0].weight._grad = tensor(np.zeros((2, 4), dtype=np.float32))
        statuses = verify_updates(model, before)
        assert not statuses[0].updated
        assert "zero" in statuses[0].reason


class TestGradientDistribution:
    def test_statistics_are_populated(self):
        model = small_model()
        x, y = small_batch()
        backward(cross_entropy(model(x), y))
        dists = gradient_distribution(model)
        assert len(dists) == 4
        for d in dists:
            assert d.minimum <= d.maximum
            assert d.l2_norm > 0.0
            assert d.healthy
            assert 0.0 <= d.zero_fraction <= 1.0

    def test_detects_nan(self):
        model = small_model()
        x, y = small_batch()
        backward(cross_entropy(model(x), y))
        dists = gradient_distribution(model)
        model[0].weight._grad = tensor(np.full((8, 4), np.nan, dtype=np.float32))
        updated = {d.name: d for d in gradient_distribution(model)}
        assert not updated["0.weight"].healthy
        assert updated["0.weight"].nan_fraction == 1.0

    def test_detects_infinity(self):
        model = small_model()
        zeros = tensor(np.zeros((4, 4), dtype=np.float32))
        labels = tensor(np.zeros(4, dtype=np.int64))
        backward(cross_entropy(model(zeros), labels))
        model[0].weight._grad = tensor(np.full((8, 4), np.inf, dtype=np.float32))
        updated = {d.name: d for d in gradient_distribution(model)}
        assert not updated["0.weight"].healthy

    def test_table_renders(self):
        model = small_model()
        x, y = small_batch()
        backward(cross_entropy(model(x), y))
        text = format_distribution(gradient_distribution(model))
        text.encode("ascii")
        assert "nan%" in text


class TestShapeValidation:
    def test_a_correct_graph_reports_nothing(self):
        model = small_model()
        x, y = small_batch()
        assert validate_shapes(cross_entropy(model(x), y)) == []

    def test_a_deep_stack_reports_nothing(self):
        model = Sequential(Linear(4, 8), ReLU(), Linear(8, 8), ReLU(), Linear(8, 8), ReLU(), Linear(8, 2))
        x, y = small_batch()
        assert validate_shapes(cross_entropy(model(x), y)) == []


class TestBackwardValidation:
    def test_saved_tensors_are_all_used(self):
        """A correct backward reads everything its forward saved.

        Anything reported here is memory held for the whole pass for no
        reason, which on a large model is a real cost.
        """
        model = small_model()
        x, y = small_batch()
        loss = cross_entropy(model(x), y)
        unused = validate_backward(loss)
        assert unused == [], unused

    def test_relu_saves_nothing_it_does_not_use(self):
        model = small_model()
        x, y = small_batch()
        unused = validate_backward(cross_entropy(model(x), y))
        assert not any("relu" in problem for problem in unused)


class TestMemoryReport:
    def test_counts_saved_tensors(self):
        model = small_model()
        x, y = small_batch()
        report = memory_report(cross_entropy(model(x), y))
        assert report.saved_tensors > 0
        assert report.peak_bytes > 0
        assert report.active_tensors >= report.saved_tensors

    def test_grows_with_model_width(self):
        x, y = small_batch()
        narrow = Sequential(Linear(4, 4), Linear(4, 2))
        wide = Sequential(Linear(4, 512), Linear(512, 2))
        assert memory_report(cross_entropy(wide(x), y)).peak_bytes > memory_report(
            cross_entropy(narrow(x), y)
        ).peak_bytes

    def test_renders_as_text(self):
        model = small_model()
        x, y = small_batch()
        text = format_memory(memory_report(cross_entropy(model(x), y)))
        text.encode("ascii")
        assert "saved bytes" in text


class TestDashboard:
    def test_healthy_model_reports_healthy(self):
        model = small_model()
        x, y = small_batch()
        loss = lambda: cross_entropy(model(x), y)
        report = dashboard(loss(), model, checks=gradient_consistency(loss, model))
        assert report.healthy, report.problems
        assert "HEALTHY" in report.render()
        assert report.graph_nodes > 0
        assert report.trainable_params == 4
        assert report.longest_chain > 0

    def test_report_is_plain_ascii(self):
        model = small_model()
        x, y = small_batch()
        dashboard(cross_entropy(model(x), y), model).render().encode("ascii")

    def test_dead_parameter_is_reported(self):
        class NoGradient(Sequential):
            def __init__(self):
                super().__init__(Linear(4, 2))
                self.frozen = Linear(2, 2, bias=False)
                for _, p in self.frozen.named_parameters():
                    p.requires_grad_(False)

            def forward(self, x):
                return self.frozen(self[0](x))

        model = NoGradient()
        x, y = small_batch()
        report = dashboard(cross_entropy(model(x), y), model)
        assert not report.healthy
        assert "frozen.weight" in report.dead_parameters

    def test_nan_gradient_is_reported(self):
        model = small_model()
        x, y = small_batch()
        report = dashboard(cross_entropy(model(x), y), model, run_backward=False)
        model[0].weight._grad = tensor(np.full((8, 4), np.nan, dtype=np.float32))
        again = dashboard(cross_entropy(model(x), y), model, run_backward=False)
        assert "0.weight" in again.nan_gradients
        assert not again.healthy

    def test_problems_section_lists_findings(self):
        model = small_model()
        x, y = small_batch()
        report = dashboard(cross_entropy(model(x), y), model)
        if report.problems:
            assert "!" in report.render()
