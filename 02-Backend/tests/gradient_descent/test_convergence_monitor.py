import pytest
from gradient_descent.convergence_monitor import ConvergenceMonitor


def test_convergence_monitor_not_converged_initially():
    monitor = ConvergenceMonitor(window=3, tol=1e-6)
    assert not monitor.converged()


def test_convergence_monitor_converges_on_flat_loss():
    monitor = ConvergenceMonitor(window=5, tol=1e-6)
    for _ in range(5):
        monitor.update(1.0)
    assert monitor.converged()


def test_convergence_monitor_does_not_converge_on_varying_loss():
    monitor = ConvergenceMonitor(window=3, tol=1e-6)
    monitor.update(1.0)
    monitor.update(2.0)
    monitor.update(1.0)
    assert not monitor.converged()


def test_convergence_monitor_reset():
    monitor = ConvergenceMonitor(window=2, tol=1e-6)
    monitor.update(1.0)
    monitor.update(1.0)
    assert monitor.converged()
    monitor.reset()
    assert not monitor.converged()


def test_convergence_monitor_tight_tolerance():
    monitor = ConvergenceMonitor(window=3, tol=1e-12)
    monitor.update(1.0)
    monitor.update(1.0 + 1e-10)
    monitor.update(1.0)
    assert not monitor.converged()


def test_convergence_monitor_window_one():
    monitor = ConvergenceMonitor(window=1, tol=1e-6)
    monitor.update(1.0)
    assert monitor.converged()


def test_convergence_monitor_window_larger_than_updates():
    monitor = ConvergenceMonitor(window=5, tol=1e-6)
    monitor.update(1.0)
    monitor.update(2.0)
    assert not monitor.converged()


def test_convergence_monitor_negative_losses():
    monitor = ConvergenceMonitor(window=3, tol=1e-6)
    monitor.update(-1.0)
    monitor.update(-1.0)
    monitor.update(-1.0)
    assert monitor.converged()


def test_convergence_monitor_loss_type_casting():
    monitor = ConvergenceMonitor(window=2, tol=1e-6)
    monitor.update(1)
    monitor.update(1)
    assert monitor.converged()


def test_convergence_monitor_empty_after_reset():
    monitor = ConvergenceMonitor(window=3, tol=1e-6)
    monitor.update(1.0)
    monitor.update(1.0)
    monitor.update(1.0)
    assert monitor.converged()
    monitor.reset()
    assert len(monitor.losses) == 0
    assert not monitor.converged()


def test_convergence_monitor_exact_window_converges():
    monitor = ConvergenceMonitor(window=4, tol=1e-6)
    monitor.update(1.0)
    monitor.update(1.0)
    monitor.update(1.0)
    monitor.update(1.0)
    assert monitor.converged()
