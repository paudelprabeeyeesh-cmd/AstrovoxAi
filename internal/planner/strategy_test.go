package planner

import "testing"

func TestBestFitSelect(t *testing.T) {
	s := NewStrategySelector(StrategyBestFit)
	free := []int{10, 20, 30, 5}
	got := s.Select(free, 15)
	if got != 20 {
		t.Errorf("best fit for 15 = %d, want 20", got)
	}
}

func TestFirstFitSelect(t *testing.T) {
	s := NewStrategySelector(StrategyFirstFit)
	free := []int{10, 20, 5}
	got := s.Select(free, 15)
	if got != 20 {
		t.Errorf("first fit for 15 = %d, want 20", got)
	}
}

func TestSelectNone(t *testing.T) {
	s := NewStrategySelector(StrategyFirstFit)
	if got := s.Select([]int{5, 10}, 15); got != -1 {
		t.Errorf("no fit should return -1, got %d", got)
	}
}
