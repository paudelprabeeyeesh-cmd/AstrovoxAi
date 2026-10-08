package planner

import (
	"testing"
)

func TestArena_AllocBytes(t *testing.T) {
	a := NewArena(100)
	b, err := a.AllocBytes(10)
	if err != nil {
		t.Fatalf("AllocBytes: %v", err)
	}
	if len(b) != 10 {
		t.Fatalf("len = %d, want 10", len(b))
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
	b := Buffer{Name: "buf1", Size: 1024}
	if b.String() != "buf1 (1024)" {
		t.Fatalf("String = %q, want buf1 (1024)", b.String())
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
	if r.Start != 5 || r.End != 5 {
		t.Fatalf("empty intersect = %+v", r)
	}
}

func TestPeakEstimator_NonOverlapping(t *testing.T) {
	e := NewPeakEstimator()
	lts := []Lifetime{
		{Start: 0, End: 5, Size: 100},
		{Start: 5, End: 10, Size: 100},
	}
	if p := e.Estimate(lts, nil); p != 100 {
		t.Fatalf("peak = %d, want 100", p)
	}
}

func TestPeakEstimator_Overlapping(t *testing.T) {
	e := NewPeakEstimator()
	lts := []Lifetime{
		{Start: 0, End: 10, Size: 100},
		{Start: 5, End: 15, Size: 200},
	}
	if p := e.Estimate(lts, nil); p != 300 {
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

func TestPoolManager_AcquireRelease(t *testing.T) {
	m := NewPoolManager(64)
	buf := m.Acquire(32)
	if len(buf) != 64 {
		t.Fatalf("len = %d, want 64", len(buf))
	}
	m.Release(buf)
	cached, blockSize := m.Stats()
	if cached != 1 || blockSize != 64 {
		t.Fatalf("stats = (%d,%d), want (1,64)", cached, blockSize)
	}
}

func TestPoolManager_MultipleAcquire(t *testing.T) {
	m := NewPoolManager(32)
	b1 := m.Acquire(16)
	b2 := m.Acquire(16)
	if len(b1) != 32 || len(b2) != 32 {
		t.Fatalf("buffer sizes = %d, %d, want 32,32", len(b1), len(b2))
	}
}

func TestBestFitSelect(t *testing.T) {
	s := NewStrategySelector(BestFit)
	free := []int{64, 128, 256}
	idx := s.Select(free, 100)
	if idx < 0 || idx >= len(free) || free[idx] != 128 {
		t.Fatalf("best fit idx = %d, want 128", idx)
	}
}

func TestFirstFitSelect(t *testing.T) {
	s := NewStrategySelector(FirstFit)
	free := []int{64, 128, 256}
	idx := s.Select(free, 100)
	if idx != 1 {
		t.Fatalf("first fit idx = %d, want 1", idx)
	}
}

func TestSelectNone(t *testing.T) {
	s := NewStrategySelector(FirstFit)
	if idx := s.Select([]int{10, 20}, 100); idx != -1 {
		t.Fatalf("expected -1, got %d", idx)
	}
}

func TestPoolManager_ExactAcquire(t *testing.T) {
	m := NewPoolManager(64)
	buf := m.Acquire(64)
	if len(buf) != 64 {
		t.Fatalf("len = %d, want 64", len(buf))
	}
}

func TestStrategySelector_ExactSize(t *testing.T) {
	s := NewStrategySelector(BestFit)
	free := []int{64, 128, 256}
	idx := s.Select(free, 64)
	if idx != 0 {
		t.Fatalf("exact fit idx = %d, want 0", idx)
	}
}
