package planner

import "fmt"

// Interval represents a half-open time interval [Start, End).
type Interval struct {
	Start int64
	End   int64
}

// Overlaps returns true if i and other share any point.
func (i Interval) Overlaps(other Interval) bool {
	return i.Start < other.End && other.Start < i.End
}

// Length returns the duration of the interval.
func (i Interval) Length() int64 {
	if i.End <= i.Start {
		return 0
	}
	return i.End - i.Start
}

// Contains returns true if point lies within the interval.
func (i Interval) Contains(point int64) bool {
	return i.Start <= point && point < i.End
}

// Intersect returns the intersection of i and other, or zero if disjoint.
func (i Interval) Intersect(other Interval) Interval {
	if !i.Overlaps(other) {
		return Interval{}
	}
	return Interval{
		Start: max(i.Start, other.Start),
		End:   min(i.End, other.End),
	}
}

func max(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}

func min(a, b int64) int64 {
	if a < b {
		return a
	}
	return b
}

// String returns a human-readable representation.
func (i Interval) String() string {
	return fmt.Sprintf("[%d, %d)", i.Start, i.End)
}
