package planner

// AllocationPlan describes a complete memory allocation plan.
type AllocationPlan struct {
	Buffers []Buffer
	Peak    int64
}

// PlanGenerator produces allocation plans from lifetimes.
type PlanGenerator struct {
	Planner   *BufferPlanner
	Estimator *PeakEstimator
}

// NewPlanGenerator creates a new plan generator.
func NewPlanGenerator() *PlanGenerator {
	return &PlanGenerator{
		Planner:   NewBufferPlanner(),
		Estimator: NewPeakEstimator(),
	}
}

// Generate produces an allocation plan.
func (g *PlanGenerator) Generate(lifetimes []Lifetime, sizeMap map[string]int) *AllocationPlan {
	buffers := g.Planner.Plan(lifetimes, sizeMap)
	peak := g.Estimator.Estimate(lifetimes, sizeMap)
	return &AllocationPlan{
		Buffers: buffers,
		Peak:    peak,
	}
}
