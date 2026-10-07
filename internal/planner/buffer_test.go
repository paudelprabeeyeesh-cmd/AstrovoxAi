package planner

import (
	"testing"
)

func TestBufferPlanner_Plan(t *testing.T) {
	lifetimes := []Lifetime{
		{"a", Interval{0, 2}},
		{"b", Interval{2, 4}},
		{"c", Interval{1, 3}},
	}
	sizeMap := map[string]int{"a": 10, "b": 10, "c": 10}

	p := NewBufferPlanner()
	buffers := p.Plan(lifetimes, sizeMap)

	if len(buffers) != 3 {
		t.Fatalf("got %d buffers, want 3", len(buffers))
	}

	colors := make(map[int]bool)
	for _, b := range buffers {
		colors[b.Color] = true
	}
	if len(colors) < 2 {
		t.Errorf("expected at least 2 colors for overlapping intervals, got %d", len(colors))
	}
}

func TestBufferPlanner_Empty(t *testing.T) {
	p := NewBufferPlanner()
	got := p.Plan(nil, nil)
	if got != nil {
		t.Error("nil input should return nil")
	}
}

func TestBufferString(t *testing.T) {
	b := Buffer{ID: "x", Size: 100, Offset: 0, Color: 1, Interval: Interval{0, 5}}
	s := b.String()
	if s == "" {
		t.Error("String should not be empty")
	}
}
