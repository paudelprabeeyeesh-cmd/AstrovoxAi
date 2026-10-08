package planner

import (
	"strings"
	"testing"
)

func TestArena_AllocBytes(t *testing.T) {
	a := NewArena(100)
	_, err := a.AllocBytes(10)
	if err != nil {
		t.Fatalf("AllocBytes: %v", err)
	}
}

func TestArena_Used(t *testing.T) {
	a := NewArena(100)
	_, _ = a.Alloc(30)
	if a.Used() != 30 {
		t.Fatalf("used = %d, want 30", a.Used())
	}
}

func TestArena_SequentialAllocs(t *testing.T) {
	a := NewArena(100)
	off0, _ := a.Alloc(10)
	off1, _ := a.Alloc(20)
	if off1 != off0+10 {
		t.Fatalf("off1 = %d, want %d", off1, off0+10)
	}
}

func TestBudgetChecker_SetBudget(t *testing.T) {
	b := NewBudgetChecker(50)
	b.SetBudget(200)
	if r := b.Remaining(30); r != 170 {
		t.Fatalf("remaining = %d, want 170", r)
	}
}

func TestBudgetChecker_CheckAtBoundary(t *testing.T) {
	b := NewBudgetChecker(100)
	if err := b.Check(100); err != nil {
		t.Fatalf("Check at boundary: %v", err)
	}
}

func TestBuffer_String(t *testing.T) {
	b := Buffer{ID: "buf1", Size: 1024}
	s := b.String()
	if !strings.Contains(s, "buf1") || !strings.Contains(s, "1024") {
		t.Fatalf("String = %q, want to contain buf1 and 1024", s)
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

func TestPlanGenerator_Empty(t *testing.T) {
	g := NewPlanGenerator()
	plan := g.Generate(nil, nil)
	if plan == nil {
		t.Fatal("expected non-nil plan")
	}
}

func TestStrategySelector_ExactSize(t *testing.T) {
	s := NewStrategySelector(StrategyBestFit)
	free := []int{64, 128, 256}
	slot := s.Select(free, 64)
	if slot != 64 {
		t.Fatalf("exact fit = %d, want 64", slot)
	}
}
