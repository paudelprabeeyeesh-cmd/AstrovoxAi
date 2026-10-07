package planner

import (
	"sort"
)

// PeakEstimator estimates the peak memory of a computation.
type PeakEstimator struct{}

// NewPeakEstimator creates a new estimator.
func NewPeakEstimator() *PeakEstimator {
	return &PeakEstimator{}
}

// Estimate returns the peak concurrent memory in bytes.
func (e *PeakEstimator) Estimate(lifetimes []Lifetime, sizeMap map[string]int) int64 {
	if len(lifetimes) == 0 {
		return 0
	}

	type event struct {
		time  int64
		delta int
	}

	events := make([]event, 0, len(lifetimes)*2)
	for _, lt := range lifetimes {
		size := int64(sizeMap[lt.TensorID])
		events = append(events, event{time: lt.Start, delta: int(size)})
		events = append(events, event{time: lt.End, delta: -int(size)})
	}

	sort.Slice(events, func(i, j int) bool {
		return events[i].time < events[j].time
	})

	var current, peak int64
	for _, ev := range events {
		current += int64(ev.delta)
		if current > peak {
			peak = current
		}
	}
	return peak
}
