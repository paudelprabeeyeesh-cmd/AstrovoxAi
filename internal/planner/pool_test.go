package planner

import "testing"

func TestPoolManager_AcquireRelease(t *testing.T) {
	m := NewPoolManager(64)
	buf := m.Acquire(64)
	if len(buf) != 64 {
		t.Errorf("buffer len = %d, want 64", len(buf))
	}
	m.Release(buf)
	cached, size := m.Stats()
	if cached != 1 {
		t.Errorf("cached = %d, want 1", cached)
	}
	if size != 64 {
		t.Errorf("block size = %d, want 64", size)
	}
}
