package memory_test

import (
	"sync"
	"testing"

	"github.com/astrovox/astrovox/internal/memory"
)

func TestMemoryPoolAcquireRelease(t *testing.T) {
	p := memory.NewPool(64)
	buf := p.Acquire()
	if len(buf) != 64 {
		t.Errorf("buffer len = %d, want 64", len(buf))
	}
	p.Release(buf)
	cached, size := p.Stats()
	if cached != 1 || size != 64 {
		t.Errorf("unexpected stats: %d, %d", cached, size)
	}
}

func TestMemoryPoolMultipleAcquire(t *testing.T) {
	p := memory.NewPool(64)
	b1 := p.Acquire()
	b2 := p.Acquire()
	if len(b1) != 64 || len(b2) != 64 {
		t.Fatal("expected 64 byte buffers")
	}
	p.Release(b1)
	p.Release(b2)
	cached, _ := p.Stats()
	if cached != 2 {
		t.Errorf("expected 2 cached, got %d", cached)
	}
}

func TestMemoryPoolReset(t *testing.T) {
	p := memory.NewPool(64)
	p.Acquire()
	p.Reset()
	cached, _ := p.Stats()
	if cached != 0 {
		t.Errorf("expected 0 cached after reset, got %d", cached)
	}
}

func TestMemoryArenaAlloc(t *testing.T) {
	a := memory.NewArena(100)
	off, err := a.Alloc(40)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if off != 0 {
		t.Errorf("offset = %d, want 0", off)
	}
	if a.Used() != 40 {
		t.Errorf("used = %d, want 40", a.Used())
	}
}

func TestMemoryArenaExhausted(t *testing.T) {
	a := memory.NewArena(10)
	_, _ = a.Alloc(5)
	_, err := a.Alloc(10)
	if err != memory.ErrArenaExhausted {
		t.Errorf("expected ErrArenaExhausted, got %v", err)
	}
}

func TestMemoryArenaReset(t *testing.T) {
	a := memory.NewArena(100)
	_, _ = a.Alloc(80)
	a.Reset()
	if a.Used() != 0 {
		t.Errorf("after reset used = %d, want 0", a.Used())
	}
	if a.Remaining() != 100 {
		t.Errorf("after reset remaining = %d, want 100", a.Remaining())
	}
}

func TestMemoryPoolConcurrent(t *testing.T) {
	p := memory.NewPool(64)
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			buf := p.Acquire()
			p.Release(buf)
		}()
	}
	wg.Wait()
}

func TestMemoryArenaMultipleAllocs(t *testing.T) {
	a := memory.NewArena(100)
	off1, _ := a.Alloc(20)
	off2, _ := a.Alloc(30)
	if off2 != off1+20 {
		t.Errorf("expected offset %d, got %d", off1+20, off2)
	}
	if a.Remaining() != 50 {
		t.Errorf("expected 50 remaining, got %d", a.Remaining())
	}
}
