package memory

import (
	"testing"
)

func TestPoolAcquireMultiple(t *testing.T) {
	p := NewPool(64)
	b1 := p.Acquire()
	b2 := p.Acquire()
	if len(b1) != 64 || len(b2) != 64 {
		t.Fatalf("expected 64 bytes each, got %d, %d", len(b1), len(b2))
	}
}

func TestPoolReleaseNil(t *testing.T) {
	p := NewPool(64)
	p.Release(nil)
	cached, _ := p.Stats()
	if cached != 0 {
		t.Fatalf("expected 0 cached blocks, got %d", cached)
	}
}

func TestPoolAcquireAfterRelease(t *testing.T) {
	p := NewPool(32)
	b1 := p.Acquire()
	p.Release(b1)
	b2 := p.Acquire()
	if &b1[0] != &b2[0] {
		t.Fatal("expected reused buffer")
	}
}

func TestPoolStatsBeforeAndAfter(t *testing.T) {
	p := NewPool(64)
	cached1, _ := p.Stats()
	if cached1 != 0 {
		t.Fatalf("expected 0 cached blocks initially, got %d", cached1)
	}
	b := p.Acquire()
	p.Release(b)
	cached2, size := p.Stats()
	if cached2 != 1 {
		t.Fatalf("expected 1 cached block, got %d", cached2)
	}
	if size != 64 {
		t.Fatalf("expected size 64, got %d", size)
	}
}

func TestArenaAllocMultiple(t *testing.T) {
	a := NewArena(1024)
	b1, err := a.Alloc(256)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	b2, err := a.Alloc(256)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(b1) != 256 || len(b2) != 256 {
		t.Fatalf("expected 256 bytes each, got %d, %d", len(b1), len(b2))
	}
}

func TestArenaResetReuse(t *testing.T) {
	a := NewArena(512)
	_, _ = a.Alloc(256)
	a.Reset()
	b, err := a.Alloc(256)
	if err != nil {
		t.Fatalf("unexpected error after reset: %v", err)
	}
	if len(b) != 256 {
		t.Fatalf("expected 256 bytes after reset, got %d", len(b))
	}
}

func TestArenaGetPool(t *testing.T) {
	a := NewArena(1024)
	p1 := a.GetPool(64)
	p2 := a.GetPool(64)
	if p1 != p2 {
		t.Fatal("expected same pool for same size")
	}
	p3 := a.GetPool(128)
	if p1 == p3 {
		t.Fatal("expected different pools for different sizes")
	}
}

func TestBufferReuserDifferentShapes(t *testing.T) {
	r := NewBufferReuser()
	b1 := r.Acquire([]int{2, 3}, "float32")
	b2 := r.Acquire([]int{3, 4}, "float32")
	if len(b1) != 6 {
		t.Fatalf("expected 6 bytes, got %d", len(b1))
	}
	if len(b2) != 12 {
		t.Fatalf("expected 12 bytes, got %d", len(b2))
	}
}

func TestBufferReuserSameShapeReuse(t *testing.T) {
	r := NewBufferReuser()
	shape := []int{2, 2}
	b1 := r.Acquire(shape, "float32")
	r.Release(shape, "float32", b1)
	b2 := r.Acquire(shape, "float32")
	if &b1[0] != &b2[0] {
		t.Fatal("expected reused buffer")
	}
}

func TestLeakDetectorMultipleRecords(t *testing.T) {
	l := NewLeakDetector()
	l.Record("tensor1")
	l.Record("tensor2")
	l.Release("tensor1")
	report := l.Report()
	if _, ok := report["tensor1"]; ok {
		t.Fatal("expected no leak for tensor1")
	}
	if _, ok := report["tensor2"]; !ok {
		t.Fatal("expected leak report for tensor2")
	}
}

func TestLeakDetectorReportEmpty(t *testing.T) {
	l := NewLeakDetector()
	report := l.Report()
	if len(report) != 0 {
		t.Fatalf("expected empty report, got %v", report)
	}
}

func TestLeakDetectorDoubleRelease(t *testing.T) {
	l := NewLeakDetector()
	l.Record("tensor1")
	l.Release("tensor1")
	l.Release("tensor1")
	report := l.Report()
	if len(report) != 0 {
		t.Fatalf("expected empty report after double release, got %v", report)
	}
}

func TestMemoryPoolZeroSize(t *testing.T) {
	p := NewPool(0)
	b := p.Acquire()
	if len(b) != 0 {
		t.Fatalf("expected 0 bytes, got %d", len(b))
	}
}

func TestMemoryPoolLargeBlock(t *testing.T) {
	p := NewPool(1024 * 1024)
	b := p.Acquire()
	if len(b) != 1024*1024 {
		t.Fatalf("expected 1MB, got %d", len(b))
	}
	p.Release(b)
}

func TestArenaLargeAllocation(t *testing.T) {
	a := NewArena(1024 * 1024)
	b, err := a.Alloc(1024 * 1024)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(b) != 1024*1024 {
		t.Fatalf("expected 1MB, got %d", len(b))
	}
}

func TestBufferReuserNilRelease(t *testing.T) {
	r := NewBufferReuser()
	r.Release([]int{2, 3}, "float32", nil)
}

func TestLeakDetectorManyRecords(t *testing.T) {
	l := NewLeakDetector()
	for i := 0; i < 100; i++ {
		l.Record("tensor")
	}
	for i := 0; i < 50; i++ {
		l.Release("tensor")
	}
	report := l.Report()
	if report["tensor"] != 50 {
		t.Fatalf("expected 50 leaked, got %d", report["tensor"])
	}
}
