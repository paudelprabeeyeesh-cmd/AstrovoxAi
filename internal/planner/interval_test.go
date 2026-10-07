package planner

import "testing"

func TestIntervalOverlaps(t *testing.T) {
	tests := []struct {
		a, b     Interval
		expected bool
	}{
		{Interval{0, 5}, Interval{5, 10}, false},
		{Interval{0, 5}, Interval{4, 10}, true},
		{Interval{0, 5}, Interval{0, 5}, true},
		{Interval{0, 5}, Interval{1, 2}, true},
		{Interval{1, 2}, Interval{0, 5}, true},
	}
	for _, tt := range tests {
		got := tt.a.Overlaps(tt.b)
		if got != tt.expected {
			t.Errorf("Overlaps(%v, %v) = %v, want %v", tt.a, tt.b, got, tt.expected)
		}
	}
}

func TestIntervalLength(t *testing.T) {
	i := Interval{0, 10}
	if i.Length() != 10 {
		t.Error("length mismatch")
	}
	j := Interval{5, 5}
	if j.Length() != 0 {
		t.Error("zero-length mismatch")
	}
	k := Interval{10, 5}
	if k.Length() != 0 {
		t.Error("negative length mismatch")
	}
}

func TestIntervalContains(t *testing.T) {
	i := Interval{0, 10}
	if !i.Contains(0) || !i.Contains(5) || !i.Contains(9) {
		t.Error("should contain interior points")
	}
	if i.Contains(10) || i.Contains(-1) {
		t.Error("should not contain boundary/outside")
	}
}

func TestIntervalIntersect(t *testing.T) {
	i := Interval{0, 10}
	j := Interval{5, 15}
	got := i.Intersect(j)
	if got.Start != 5 || got.End != 10 {
		t.Errorf("intersect = %v, want [5, 10)", got)
	}
	empty := Interval{0, 5}.Intersect(Interval{5, 10})
	if !empty.Contains(0) {
		t.Error("disjoint intersection should be empty")
	}
}
