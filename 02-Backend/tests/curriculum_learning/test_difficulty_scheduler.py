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

    def test_max_epochs_enforced(self):
        scheduler = DifficultyScheduler(
            start_difficulty=0.0,
            end_difficulty=1.0,
            schedule="linear",
            warmup_epochs=10,
            max_epochs=2,
        )
        assert scheduler.max_epochs >= scheduler.warmup_epochs + 1

    def test_step_returns_difficulty(self):
        scheduler = DifficultyScheduler()
        difficulty = scheduler.step()
        assert difficulty == scheduler.current_difficulty

    def test_difficulty_history_populated(self):
        scheduler = DifficultyScheduler()
        assert scheduler.difficulty_history == []
        scheduler.step()
        assert len(scheduler.difficulty_history) == 1

    def test_filter_samples_empty(self):
        scheduler = DifficultyScheduler()
        filtered_samples, filtered_difficulties = scheduler.filter_samples([], [])
        assert filtered_samples == []
        assert filtered_difficulties == []

    def test_filter_samples_no_above_threshold(self):
        scheduler = DifficultyScheduler(start_difficulty=0.0, end_difficulty=0.2)
        scheduler.step()
        samples = [1.0, 2.0, 3.0]
        scores = [0.5, 0.6, 0.7]
        filtered_samples, filtered_difficulties = scheduler.filter_samples(samples, scores)
        assert filtered_samples == []

    def test_invalid_schedule_defaults_to_end_difficulty(self):
        scheduler = DifficultyScheduler(
            start_difficulty=0.0,
            end_difficulty=1.0,
            schedule="invalid",
            max_epochs=2,
        )
        scheduler.step()
        assert scheduler.current_difficulty == scheduler.end_difficulty

    def test_progress_at_warmup_epochs(self):
        scheduler = DifficultyScheduler(
            start_difficulty=0.0,
            end_difficulty=1.0,
            schedule="linear",
            warmup_epochs=5,
            max_epochs=10,
        )
        for _ in range(5):
            scheduler.step()
        assert scheduler._compute_progress() == 0.0

    def test_progress_after_warmup_epochs(self):
        scheduler = DifficultyScheduler(
            start_difficulty=0.0,
            end_difficulty=1.0,
            schedule="linear",
            warmup_epochs=5,
            max_epochs=10,
        )
        for _ in range(6):
            scheduler.step()
        assert scheduler._compute_progress() > 0.0

    def test_filter_samples_mismatched_lengths(self):
        scheduler = DifficultyScheduler()
        scheduler.step()
        samples = [1.0, 2.0, 3.0]
        scores = [0.1]
        filtered_samples, filtered_difficulties = scheduler.filter_samples(samples, scores)
        assert len(filtered_samples) == 1
        assert len(filtered_difficulties) == 1
