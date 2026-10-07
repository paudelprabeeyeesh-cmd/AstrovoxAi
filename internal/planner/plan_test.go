package planner

import "testing"

func TestPlanGenerator_Generate(t *testing.T) {
	g := NewPlanGenerator()
	lifetimes := []Lifetime{
		{"a", Interval{0, 3}},
		{"b", Interval{3, 6}},
	}
	sizeMap := map[string]int{"a": 100, "b": 100}

	plan := g.Generate(lifetimes, sizeMap)
	if plan == nil {
		t.Fatal("plan should not be nil")
	}
	if plan.Peak != 100 {
		t.Errorf("peak = %d, want 100", plan.Peak)
	}
	if len(plan.Buffers) != 2 {
		t.Errorf("got %d buffers, want 2", len(plan.Buffers))
	}
}
