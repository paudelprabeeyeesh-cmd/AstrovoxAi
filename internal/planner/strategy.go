package planner

// Strategy selects the allocation strategy.
type Strategy string

const (
	StrategyBestFit  Strategy = "best_fit"
	StrategyFirstFit Strategy = "first_fit"
)

// StrategySelector chooses buffers according to the configured strategy.
type StrategySelector struct {
	Strategy Strategy
}

// NewStrategySelector creates a selector.
func NewStrategySelector(s Strategy) *StrategySelector {
	return &StrategySelector{Strategy: s}
}

// Select returns a buffer index from available free slots.
func (s *StrategySelector) Select(freeSlots []int, requiredSize int) int {
	if len(freeSlots) == 0 {
		return -1
	}
	switch s.Strategy {
	case StrategyBestFit:
		best := -1
		bestSize := int(^uint(0) >> 1)
		for _, slot := range freeSlots {
			if slot >= requiredSize && slot < bestSize {
				bestSize = slot
				best = slot
			}
		}
		return best
	case StrategyFirstFit:
		for _, slot := range freeSlots {
			if slot >= requiredSize {
				return slot
			}
		}
		return -1
	default:
		return freeSlots[0]
	}
}
