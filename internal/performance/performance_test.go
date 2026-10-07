package performance

import "testing"

func TestLazyValue(t *testing.T) {
	count := 0
	lv := NewLazyValue(func() interface{} {
		count++
		return 42
	})
	v1 := lv.Get()
	v2 := lv.Get()
	if v1 != 42 || v2 != 42 {
		t.Fatalf("expected 42, got %v, %v", v1, v2)
	}
	if count != 1 {
		t.Errorf("expected 1 computation, got %d", count)
	}
}

func TestSIMDVector_Add(t *testing.T) {
	v1 := NewSIMDVector(3)
	v1.Data = []float64{1, 2, 3}
	v2 := NewSIMDVector(3)
	v2.Data = []float64{4, 5, 6}
	out, err := v1.Add(v2)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if out.Data[0] != 5 || out.Data[1] != 7 || out.Data[2] != 9 {
		t.Errorf("unexpected result: %v", out.Data)
	}
}

func TestSIMDVector_AddMismatch(t *testing.T) {
	v1 := NewSIMDVector(2)
	v2 := NewSIMDVector(3)
	_, err := v1.Add(v2)
	if err == nil {
		t.Fatal("expected size mismatch error")
	}
}

func TestAlignToCacheLine(t *testing.T) {
	if AlignToCacheLine(64) != 64 {
		t.Error("expected 64")
	}
	if AlignToCacheLine(65) != 128 {
		t.Error("expected 128")
	}
	if AlignToCacheLine(0) != 0 {
		t.Error("expected 0")
	}
}

func TestNumCPU(t *testing.T) {
	cpus := NumCPU()
	if cpus <= 0 {
		t.Errorf("expected positive cpu count, got %d", cpus)
	}
}

func TestParallelFor(t *testing.T) {
	sum := 0
	ParallelFor(0, 10, func(i int) { sum += i })
	if sum != 45 {
		t.Errorf("expected 45, got %d", sum)
	}
}

func TestParallelForEmpty(t *testing.T) {
	ParallelFor(5, 5, func(i int) {})
}

func TestParallelForNegative(t *testing.T) {
	ParallelFor(-1, 5, func(i int) {})
}

func TestSizeMismatchError(t *testing.T) {
	err := &SizeMismatchError{}
	if err.Error() != "vector size mismatch" {
		t.Errorf("unexpected error: %v", err)
	}
}
