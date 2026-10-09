import numpy as np
import pytest
from contrastive_learning.temperature_scheduler import TemperatureScheduler


class TestTemperatureScheduler:
    def test_initialization_default(self):
        scheduler = TemperatureScheduler()
        assert scheduler.get() == pytest.approx(0.07)

    def test_initialization_custom(self):
        scheduler = TemperatureScheduler(initial_temperature=0.1, min_temperature=0.01, max_temperature=0.5)
        assert scheduler.get() == pytest.approx(0.1)

    def test_invalid_temperature(self):
        with pytest.raises(ValueError):
            TemperatureScheduler(initial_temperature=0.0)
        with pytest.raises(ValueError):
            TemperatureScheduler(initial_temperature=-1.0)
        with pytest.raises(ValueError):
            TemperatureScheduler(min_temperature=0.1, max_temperature=0.01)

    def test_invalid_schedule(self):
        with pytest.raises(ValueError):
            TemperatureScheduler(schedule="unknown")

    def test_constant_schedule(self):
        scheduler = TemperatureScheduler(initial_temperature=0.1, schedule="constant")
        for _ in range(100):
            scheduler.step()
        assert scheduler.get() == pytest.approx(0.1)

    def test_step_schedule(self):
        scheduler = TemperatureScheduler(initial_temperature=0.1, schedule="step", step_size=10, gamma=0.5)
        for _ in range(9):
            scheduler.step()
        assert scheduler.get() == pytest.approx(0.1)
        scheduler.step()
        assert scheduler.get() == pytest.approx(0.05)

    def test_step_schedule_min(self):
        scheduler = TemperatureScheduler(initial_temperature=0.1, min_temperature=0.03, schedule="step", step_size=1, gamma=0.1)
        for _ in range(5):
            scheduler.step()
        assert scheduler.get() == pytest.approx(0.03)

    def test_exponential_schedule(self):
        scheduler = TemperatureScheduler(initial_temperature=0.1, schedule="exponential", step_size=1, gamma=0.5)
        for _ in range(2):
            scheduler.step()
        expected = 0.1 * (0.5 ** 2)
        assert scheduler.get() == pytest.approx(expected)

    def test_cosine_schedule(self):
        scheduler = TemperatureScheduler(initial_temperature=0.1, min_temperature=0.0, schedule="cosine", step_size=100)
        for _ in range(100):
            scheduler.step()
        assert 0.0 <= scheduler.get() <= 0.1

    def test_reset(self):
        scheduler = TemperatureScheduler(initial_temperature=0.1, schedule="step", step_size=1, gamma=0.5)
        scheduler.step()
        assert scheduler.get() < 0.1
        scheduler.reset()
        assert scheduler.get() == pytest.approx(0.1)
