package planner

import "testing"

func TestArena_Alloc(t *testing.T) {
	a := NewArena(100)
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
	if a.Remaining() != 60 {
		t.Errorf("remaining = %d, want 60", a.Remaining())
	}
}

func TestArena_Exhausted(t *testing.T) {
	a := NewArena(10)
	_, _ = a.Alloc(5)
	_, err := a.Alloc(10)
	if err != ErrArenaExhausted {
		t.Errorf("expected ErrArenaExhausted, got %v", err)
	}
}

func TestArena_Reset(t *testing.T) {
	a := NewArena(100)
	_, _ = a.Alloc(80)
	a.Reset()
	if a.Used() != 0 {
		t.Errorf("after reset used = %d, want 0", a.Used())
	}
	if a.Remaining() != 100 {
		t.Errorf("after reset remaining = %d, want 100", a.Remaining())
	}
}
