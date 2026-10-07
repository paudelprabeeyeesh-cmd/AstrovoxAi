package planner

import "testing"

func TestPeakEstimator_Estimate(t *testing.T) {
	e := NewPeakEstimator()
	lifetimes := []Lifetime{
		{"a", Interval{0, 5}},
		{"b", Interval{3, 8}},
		{"c", Interval{8, 10}},
	}
	sizeMap := map[string]int{"a": 10, "b": 20, "c": 10}

	peak := e.Estimate(lifetimes, sizeMap)
	if peak != 30 {
		t.Errorf("peak = %d, want 30", peak)
	}
}

func TestPeakEstimator_Empty(t *testing.T) {
	e := NewPeakEstimator()
	if got := e.Estimate(nil, nil); got != 0 {
		t.Errorf("empty input peak = %d, want 0", got)
	}
}
