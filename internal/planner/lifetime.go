package planner

import (
	"sort"
)

// Lifetime describes when a tensor value is live.
type Lifetime struct {
	TensorID string
	Interval
}

// ByStart sorts lifetimes by ascending start time.
type ByStart []Lifetime

func (a ByStart) Len() int      { return len(a) }
func (a ByStart) Swap(i, j int) { a[i], a[j] = a[j], a[i] }
func (a ByStart) Less(i, j int) bool {
	if a[i].Start != a[j].Start {
		return a[i].Start < a[j].Start
	}
	return a[i].End < a[j].End
}

// ByEnd sorts lifetimes by ascending end time.
type ByEnd []Lifetime

func (a ByEnd) Len() int      { return len(a) }
func (a ByEnd) Swap(i, j int) { a[i], a[j] = a[j], a[i] }
func (a ByEnd) Less(i, j int) bool {
	return a[i].End < a[j].End
}

// OpInfo describes a single operation for lifetime analysis.
type OpInfo struct {
	Name    string
	Inputs  []string
	Outputs []string
}

// AnalyzeLifetimes computes live intervals from an op sequence.
func AnalyzeLifetimes(ops []OpInfo) []Lifetime {
	if len(ops) == 0 {
		return nil
	}

	firstDef := make(map[string]int64)
	lastUse := make(map[string]int64)

	for step, op := range ops {
		for _, inp := range op.Inputs {
			if _, ok := firstDef[inp]; !ok {
				firstDef[inp] = int64(step)
			}
			lastUse[inp] = int64(step)
		}
		for _, out := range op.Outputs {
			if _, ok := firstDef[out]; !ok {
				firstDef[out] = int64(step)
			}
			lastUse[out] = int64(step)
		}
	}

	lifetimes := make([]Lifetime, 0, len(firstDef))
	for tensor, start := range firstDef {
		end := lastUse[tensor]
		if end < start {
			end = start
		}
		lifetimes = append(lifetimes, Lifetime{
			TensorID: tensor,
			Interval: Interval{Start: start, End: end + 1},
		})
	}

	sort.Sort(ByStart(lifetimes))
	return lifetimes
}
