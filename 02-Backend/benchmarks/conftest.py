"""Pytest configuration for benchmark suite."""

import pytest

def pytest_configure(config):
    """Configure pytest for benchmarking."""
    # Enable benchmark plugin if available
    if hasattr(config, 'pluginmanager'):
        if config.pluginmanager.has_plugin('benchmark'):
            # Configure benchmark settings
            config.option.benchmark_min_rounds = 5
            config.option.benchmark_max_time = 5.0
            config.option.benchmark_min_time = 0.000005
            config.option.benchmark_timer = time.perf_counter
            config.option.benchmark_disable_gc = False
            config.option.benchmark_warmup = True
            config.option.benchmark_warmup_iterations = 100000

def pytest_runtest_setup(item):
    """Setup for each test."""
    # Enable tracemalloc for memory tracking in tests
    import tracemalloc
    if not tracemalloc.is_tracing():
        tracemalloc.start()

def pytest_runtest_teardown(item):
    """Teardown for each test."""
    # Optionally stop tracemalloc
    pass