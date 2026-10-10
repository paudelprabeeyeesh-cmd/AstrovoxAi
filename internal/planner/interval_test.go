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
	if empty.Contains(0) {
		t.Error("disjoint intersection should be empty")
	}
}

func TestInterval_Overlaps(t *testing.T) {
	i1 := Interval{Start: 0, End: 10}
	i2 := Interval{Start: 5, End: 15}
	if !i1.Overlaps(i2) {
		t.Fatal("expected overlap")
	}
	i3 := Interval{Start: 20, End: 30}
	if i1.Overlaps(i3) {
		t.Fatal("expected no overlap")
	}
}

func TestInterval_Length(t *testing.T) {
	i := Interval{Start: 0, End: 10}
	if i.Length() != 10 {
		t.Fatalf("length = %d, want 10", i.Length())
	}
}

func TestInterval_Contains(t *testing.T) {
	i := Interval{Start: 0, End: 10}
	if !i.Contains(5) {
		t.Fatal("expected 5 in interval")
	}
	if i.Contains(10) {
		t.Fatal("expected 10 not in [0,10)")
	}
}

func TestInterval_Intersect(t *testing.T) {
	i1 := Interval{Start: 0, End: 10}
	i2 := Interval{Start: 5, End: 15}
	r := i1.Intersect(i2)
	if r.Start != 5 || r.End != 10 {
		t.Fatalf("intersect = %+v, want {5 10}", r)
	}
}

func TestInterval_EmptyIntersect(t *testing.T) {
	i1 := Interval{Start: 0, End: 5}
	i2 := Interval{Start: 5, End: 10}
	r := i1.Intersect(i2)
	if r.Start != 0 || r.End != 0 {
		t.Fatalf("empty intersect = [%d, %d), want [0, 0)", r.Start, r.End)
	}
}
