package memory

import (
	"testing"
)

func TestPoolAcquireRelease(t *testing.T) {
	p := NewPool(64)
	b := p.Acquire()
	if len(b) != 64 {
		t.Fatalf("expected 64 bytes, got %d", len(b))
	}
	p.Release(b)
	cached, _ := p.Stats()
	if cached != 1 {
		t.Fatalf("expected 1 cached block, got %d", cached)
	}
}

func TestPoolReset(t *testing.T) {
	p := NewPool(64)
	p.Acquire()
	p.Reset()
	cached, _ := p.Stats()
	if cached != 0 {
		t.Fatalf("expected 0 cached blocks after reset, got %d", cached)
	}
}

func TestArenaAllocReset(t *testing.T) {
	a := NewArena(1024)
	b, err := a.Alloc(128)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(b) != 128 {
		t.Fatalf("expected 128 bytes, got %d", len(b))
	}
	a.Reset()
	b2, err := a.Alloc(128)
	if err != nil {
		t.Fatalf("unexpected error after reset: %v", err)
	}
	if len(b2) != 128 {
		t.Fatalf("expected 128 bytes after reset, got %d", len(b2))
	}
}

func TestArenaExhausted(t *testing.T) {
	a := NewArena(64)
	_, err := a.Alloc(128)
	if err == nil {
		t.Fatal("expected error for exhausted arena")
	}
}

func TestBufferReuserAcquireRelease(t *testing.T) {
	r := NewBufferReuser()
	shape := []int{2, 3}
	buf := r.Acquire(shape, "float32")
	if buf == nil {
		t.Fatal("expected non-nil buffer")
	}
	r.Release(shape, "float32", buf)
}

func TestLeakDetector(t *testing.T) {
	l := NewLeakDetector()
	l.Record("tensor1")
	l.Release("tensor1")
	report := l.Report()
	if len(report) != 0 {
		t.Fatalf("expected no leaks, got %v", report)
	}
}

func TestLeakDetectorLeak(t *testing.T) {
	l := NewLeakDetector()
	l.Record("tensor1")
	report := l.Report()
	if _, ok := report["tensor1"]; !ok {
		t.Fatal("expected leak report for tensor1")
	}
}

func TestPoolNilRelease(t *testing.T) {
	p := NewPool(64)
	p.Release(nil)
}
