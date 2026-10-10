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

func TestPeakEstimator_NonOverlapping(t *testing.T) {
	e := NewPeakEstimator()
	lts := []Lifetime{
		{TensorID: "a", Start: 0, End: 5},
		{TensorID: "b", Start: 5, End: 10},
	}
	sizes := map[string]int{"a": 100, "b": 100}
	if p := e.Estimate(lts, sizes); p != 100 {
		t.Fatalf("peak = %d, want 100", p)
	}
}

func TestPeakEstimator_Overlapping(t *testing.T) {
	e := NewPeakEstimator()
	lts := []Lifetime{
		{TensorID: "a", Start: 0, End: 10},
		{TensorID: "b", Start: 5, End: 15},
	}
	sizes := map[string]int{"a": 100, "b": 200}
	if p := e.Estimate(lts, sizes); p != 300 {
		t.Fatalf("peak = %d, want 300", p)
	}
}
