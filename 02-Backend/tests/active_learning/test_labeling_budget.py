import pytest
from active_learning.labeling_budget import LabelingBudget


class TestLabelingBudget:
    def test_initialization(self):
        budget = LabelingBudget(total_budget=100)
        assert budget.total_budget == 100
        assert budget.spent() == 0
        assert budget.remaining() == 100
        assert budget.utilization() == pytest.approx(0.0)
        assert not budget.is_exhausted()

    def test_negative_budget_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            LabelingBudget(total_budget=-5)

    def test_zero_budget_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            LabelingBudget(total_budget=0)

    def test_consume_success(self):
        budget = LabelingBudget(total_budget=10)
        assert budget.consume(3) is True
        assert budget.spent() == 3
        assert budget.remaining() == 7
        assert budget.utilization() == pytest.approx(0.3)

    def test_consume_default_amount(self):
        budget = LabelingBudget(total_budget=5)
        budget.consume()
        assert budget.spent() == 1
        assert budget.remaining() == 4

    def test_consume_over_budget_fails(self):
        budget = LabelingBudget(total_budget=5)
        assert budget.consume(3) is True
        assert budget.consume(3) is False
        assert budget.spent() == 3
        assert budget.remaining() == 2

    def test_consume_exact_budget(self):
        budget = LabelingBudget(total_budget=5)
        assert budget.consume(5) is True
        assert budget.is_exhausted()
        assert budget.utilization() == pytest.approx(1.0)
        assert budget.consume(1) is False

    def test_utilization(self):
        budget = LabelingBudget(total_budget=10)
        budget.consume(5)
        assert budget.utilization() == pytest.approx(0.5)
        budget.consume(5)
        assert budget.utilization() == pytest.approx(1.0)

    def test_history_records_consumption(self):
        budget = LabelingBudget(total_budget=10)
        budget.consume(2)
        budget.consume(3)
        history = budget.get_history()
        assert len(history) == 2
        assert history[0]["amount"] == 2
        assert history[0]["cumulative"] == 2
        assert history[1]["amount"] == 3
        assert history[1]["cumulative"] == 5
        assert "timestamp" in history[0]

    def test_reset(self):
        budget = LabelingBudget(total_budget=10)
        budget.consume(7)
        budget.reset()
        assert budget.spent() == 0
        assert budget.remaining() == 10
        assert budget.utilization() == pytest.approx(0.0)
        assert not budget.is_exhausted()
        assert budget.get_history() == []

    def test_repr(self):
        budget = LabelingBudget(total_budget=10)
        budget.consume(3)
        r = repr(budget)
        assert "total=10" in r
        assert "spent=3" in r
        assert "remaining=7" in r

    def test_sequential_consume(self):
        budget = LabelingBudget(total_budget=20)
        for i in range(5):
            assert budget.consume(2) is True
        assert budget.spent() == 10
        assert budget.remaining() == 10
        assert len(budget.get_history()) == 5

    def test_get_history_returns_copy(self):
        budget = LabelingBudget(total_budget=10)
        budget.consume(1)
        h1 = budget.get_history()
        h1.append({"fake": True})
        assert len(budget.get_history()) == 1
