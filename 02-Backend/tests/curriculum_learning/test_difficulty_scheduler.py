import pytest
from curriculum_learning.difficulty_scheduler import DifficultyScheduler


class TestDifficultyScheduler:
    def test_initial_state(self):
        scheduler = DifficultyScheduler()
        assert scheduler.current_difficulty == scheduler.start_difficulty
        assert scheduler.epoch == 0
        assert scheduler.difficulty_history == []

    def test_step_increments_epoch(self):
        scheduler = DifficultyScheduler()
        scheduler.step()
        assert scheduler.epoch == 1

    def test_linear_schedule(self):
        scheduler = DifficultyScheduler(
            start_difficulty=0.0,
            end_difficulty=1.0,
            schedule="linear",
            max_epochs=10,
        )
        scheduler.step()
        assert 0.0 <= scheduler.current_difficulty <= 1.0

    def test_filter_samples(self):
        scheduler = DifficultyScheduler(
            start_difficulty=0.0,
            end_difficulty=1.0,
            schedule="linear",
            max_epochs=10,
        )
        scheduler.step()
        samples = [1.0, 2.0, 3.0]
        scores = [0.1, 0.5, 0.9]
        filtered_samples, filtered_difficulties = scheduler.filter_samples(samples, scores)
        assert all(d <= scheduler.current_difficulty for d in filtered_difficulties)

    def test_reset(self):
        scheduler = DifficultyScheduler()
        scheduler.step()
        scheduler.reset()
        assert scheduler.epoch == 0
        assert scheduler.current_difficulty == scheduler.start_difficulty
        assert scheduler.difficulty_history == []

    def test_difficulty_report(self):
        scheduler = DifficultyScheduler()
        report = scheduler.get_difficulty_report()
        assert "epoch" in report
        assert "current_difficulty" in report
        assert "schedule" in report
        assert "history_length" in report

    def test_exponential_schedule(self):
        scheduler = DifficultyScheduler(
            start_difficulty=0.1,
            end_difficulty=1.0,
            schedule="exponential",
            max_epochs=10,
        )
        for _ in range(10):
            scheduler.step()
        assert scheduler.current_difficulty <= 1.0

    def test_root_schedule(self):
        scheduler = DifficultyScheduler(
            start_difficulty=0.0,
            end_difficulty=1.0,
            schedule="root",
            max_epochs=10,
        )
        for _ in range(10):
            scheduler.step()
        assert 0.0 <= scheduler.current_difficulty <= 1.0

    def test_step_schedule(self):
        scheduler = DifficultyScheduler(
            start_difficulty=0.0,
            end_difficulty=1.0,
            schedule="step",
            max_epochs=10,
        )
        for _ in range(10):
            scheduler.step()
        assert 0.0 <= scheduler.current_difficulty <= 1.0
