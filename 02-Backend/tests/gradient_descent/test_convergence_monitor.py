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
