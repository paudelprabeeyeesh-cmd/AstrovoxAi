package planner

import (
	"container/heap"
	"fmt"
	"sort"
)

// Buffer describes a memory buffer assigned to a tensor lifetime.
type Buffer struct {
	ID     string
	Size   int
	Offset int
	Color  int
	Interval
}

func (b Buffer) String() string {
	return fmt.Sprintf("buffer{id=%s size=%d offset=%d color=%d %s}", b.ID, b.Size, b.Offset, b.Color, b.Interval)
}

type heapItem struct {
	End    int64
	Color  int
	Buffer *Buffer
}

// minHeap is a min-heap ordered by End.
type minHeap []heapItem

func (h minHeap) Len() int            { return len(h) }
func (h minHeap) Less(i, j int) bool  { return h[i].End < h[j].End }
func (h minHeap) Swap(i, j int)       { h[i], h[j] = h[j], h[i] }

func (h *minHeap) Push(x interface{}) {
	*h = append(*h, x.(heapItem))
}

func (h *minHeap) Pop() interface{} {
	old := *h
	n := len(old)
	item := old[n-1]
	*h = old[:n-1]
	return item
}

// BufferPlanner assigns buffers to lifetimes via interval coloring.
type BufferPlanner struct{}

// NewBufferPlanner returns a new planner.
func NewBufferPlanner() *BufferPlanner {
	return &BufferPlanner{}
}

// Plan computes a buffer assignment. sizeMap provides sizes in bytes.
func (p *BufferPlanner) Plan(lifetimes []Lifetime, sizeMap map[string]int) []Buffer {
	if len(lifetimes) == 0 {
		return nil
	}

	sorted := make([]Lifetime, len(lifetimes))
	copy(sorted, lifetimes)

	sort.Slice(sorted, func(i, j int) bool {
		if sorted[i].Start != sorted[j].Start {
			return sorted[i].Start < sorted[j].Start
		}
		return sorted[i].End > sorted[j].End
	})

	active := make(minHeap, 0)
	heap.Init(&active)

	released := make(map[int]*Buffer)
	colorCounter := 0
	offset := 0
	var result []Buffer

	for _, lt := range sorted {
		for active.Len() > 0 && active[0].End <= lt.Start {
			entry := heap.Pop(&active).(heapItem)
			released[entry.Color] = entry.Buffer
		}

		var buf *Buffer
		if len(released) > 0 {
			for _, b := range released {
				buf = b
				buf.Interval = lt.Interval
				delete(released, buf.Color)
				break
			}
		} else {
			colorCounter++
			buf = &Buffer{Color: colorCounter}
		}

		size := sizeMap[lt.TensorID]
		buf.ID = lt.TensorID
		buf.Size = size
		if buf.Offset == 0 && buf.Color > colorCounter {
			buf.Offset = offset
			offset += size
		}
		buf.Interval = lt.Interval

		result = append(result, *buf)
		heap.Push(&active, heapItem{End: lt.End, Color: buf.Color, Buffer: buf})
	}

	return result
}
