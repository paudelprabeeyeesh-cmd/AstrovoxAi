package planner

import "testing"

func TestBudgetChecker_Check(t *testing.T) {
	b := NewBudgetChecker(100)
	if err := b.Check(80); err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if err := b.Check(120); err != ErrOverBudget {
		t.Error("expected ErrOverBudget")
	}
}

func TestBudgetChecker_Remaining(t *testing.T) {
	b := NewBudgetChecker(100)
	if got := b.Remaining(30); got != 70 {
		t.Errorf("remaining = %d, want 70", got)
	}
	if got := b.Remaining(150); got != 0 {
		t.Errorf("over budget remaining = %d, want 0", got)
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
