package planner

import "errors"

// ErrOverBudget is returned when a plan exceeds the memory budget.
var ErrOverBudget = errors.New("memory budget exceeded")

// BudgetChecker validates plans against a budget.
type BudgetChecker struct {
	Budget int64
}

// NewBudgetChecker creates a checker.
func NewBudgetChecker(budget int64) *BudgetChecker {
	return &BudgetChecker{Budget: budget}
}

// Check validates that peak usage fits within budget.
func (b *BudgetChecker) Check(peak int64) error {
	if peak > b.Budget {
		return ErrOverBudget
	}
	return nil
}

// SetBudget updates the budget.
func (b *BudgetChecker) SetBudget(budget int64) {
	b.Budget = budget
}

// Remaining returns remaining budget after peak usage.
func (b *BudgetChecker) Remaining(peak int64) int64 {
	if peak > b.Budget {
		return 0
	}
	return b.Budget - peak
}
