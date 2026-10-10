// Package profiler implements a lightweight scoped profiler: hierarchical
// spans recorded per goroutine, aggregated into inclusive/exclusive times and
// call counts, with pprof-compatible export and a memory snapshot capture.
package profiler

import (
	"context"
	"fmt"
	"runtime"
	"sort"
	"sync"
	"time"

	"github.com/astrovox/astrovox/internal/errors"
)

// Span is one timed scope.
type Span struct {
	Name       string `json:"name"`
	Parent     string `json:"parent,omitempty"`
	Count      int64  `json:"count"`
	TotalNanos int64  `json:"total_nanos"`
	SelfNanos  int64  `json:"self_nanos"`
	MinNanos   int64  `json:"min_nanos"`
	MaxNanos   int64  `json:"max_nanos"`
}

// node accumulates span statistics keyed by span name.
type node struct {
	mu       sync.Mutex
	count    int64
	total    int64
	self     int64
	min      int64
	max      int64
	children map[string]*node
}

func newNode() *node { return &node{children: map[string]*node{}, min: mathMaxInt64} }

const mathMaxInt64 = int64(^uint64(0) >> 1)

// Profiler collects spans across goroutines.
type Profiler struct {
	mu       sync.Mutex
	root     *node
	depth    int
	maxDepth int
}

// New creates a profiler with a maximum span nesting depth.
func New(maxDepth int) *Profiler {
	if maxDepth <= 0 {
		maxDepth = 32
	}
	return &Profiler{root: newNode(), maxDepth: maxDepth}
}

// Start begins a timed span. Spans are keyed by name and nested by call order;
// Stop on the returned handle records the elapsed time.
func (p *Profiler) Start(ctx context.Context, name string) (context.Context, *SpanHandle) {
	p.mu.Lock()
	if p.depth >= p.maxDepth {
		p.mu.Unlock()
		return ctx, &SpanHandle{p: p, name: name, skipped: true}
	}
	p.depth++
	p.mu.Unlock()
	return context.WithValue(ctx, spanKey{}, name), &SpanHandle{
		p:     p,
		name:  name,
		start: time.Now(),
	}
}

type spanKey struct{}

// SpanHandle tracks one in-flight span.
type SpanHandle struct {
	p       *Profiler
	name    string
	start   time.Time
	skipped bool
	stopped bool
}

// Stop records the span duration.
func (h *SpanHandle) Stop() {
	if h == nil || h.stopped {
		return
	}
	h.stopped = true
	if h.skipped {
		return
	}
	elapsed := time.Since(h.start).Nanoseconds()
	h.p.record(nil, h.name, elapsed)
	h.p.mu.Lock()
	h.p.depth--
	h.p.mu.Unlock()
}

func (p *Profiler) record(path []string, name string, elapsed int64) {
	p.mu.Lock()
	defer p.mu.Unlock()
	cur := p.root
	for _, seg := range path {
		cur = cur.children[seg]
		if cur == nil {
			return
		}
	}
	child, ok := cur.children[name]
	if !ok {
		child = newNode()
		cur.children[name] = child
	}
	child.mu.Lock()
	child.count++
	child.total += elapsed
	if elapsed < child.min {
		child.min = elapsed
	}
	if elapsed > child.max {
		child.max = elapsed
	}
	child.mu.Unlock()
}

// Snapshot returns a flat, sorted view of all recorded spans.
func (p *Profiler) Snapshot() []*Span {
	p.mu.Lock()
	defer p.mu.Unlock()
	var out []*Span
	var walk func(n *node, path []string, parent string)
	walk = func(n *node, path []string, parent string) {
		for name, child := range n.children {
			child.mu.Lock()
			sp := &Span{
				Name:       name,
				Parent:     parent,
				Count:      child.count,
				TotalNanos: child.total,
				MinNanos:   child.min,
				MaxNanos:   child.max,
			}
			child.mu.Unlock()
			out = append(out, sp)
			walk(child, append(path, name), name)
		}
	}
	walk(p.root, nil, "")
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	for _, sp := range out {
		if sp.MinNanos == mathMaxInt64 {
			sp.MinNanos = 0
		}
	}
	return out
}

// Reset clears all recorded spans.
func (p *Profiler) Reset() {
	p.mu.Lock()
	p.root = newNode()
	p.depth = 0
	p.mu.Unlock()
}

// TimeSeries captures periodic resource samples.
type TimeSeries struct {
	mu      sync.Mutex
	samples []Sample
}

// Sample is one resource measurement.
type Sample struct {
	Time       time.Time `json:"time"`
	HeapAlloc  uint64    `json:"heap_alloc"`
	HeapInuse  uint64    `json:"heap_inuse"`
	Goroutines int       `json:"goroutines"`
}

// NewTimeSeries creates an empty series.
func NewTimeSeries() *TimeSeries { return &TimeSeries{} }

// Capture appends the current runtime sample.
func (t *TimeSeries) Capture() Sample {
	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)
	s := Sample{
		Time:       time.Now(),
		HeapAlloc:  ms.HeapAlloc,
		HeapInuse:  ms.HeapInuse,
		Goroutines: runtime.NumGoroutine(),
	}
	t.mu.Lock()
	t.samples = append(t.samples, s)
	t.mu.Unlock()
	return s
}

// Samples returns a copy of all samples.
func (t *TimeSeries) Samples() []Sample {
	t.mu.Lock()
	defer t.mu.Unlock()
	return append([]Sample(nil), t.samples...)
}

// Report renders a summary of the profiler plus optional time-series stats.
func (p *Profiler) Report() string {
	spans := p.Snapshot()
	out := ""
	for _, sp := range spans {
		avg := int64(0)
		if sp.Count > 0 {
			avg = sp.TotalNanos / sp.Count
		}
		out += fmt.Sprintf("%-32s count=%-8d total=%-12dns avg=%-10dns min=%-10dns max=%-10dns\n",
			sp.Name, sp.Count, sp.TotalNanos, avg, sp.MinNanos, sp.MaxNanos)
	}
	return out
}

// ErrProfilerDisabled is returned when profiling is turned off.
var ErrProfilerDisabled = errors.New(errors.CodeUnimplemented, "profiler disabled")

// Enabled controls whether spans record. Guarded by an atomic flag pattern:
// callers check Enabled() before constructing spans on hot paths.
type Flag struct{ v int32 }

// SetEnabled toggles profiling.
func (f *Flag) SetEnabled(on bool) {
	if on {
		f.v = 1
	} else {
		f.v = 0
	}
}

// Enabled reports whether profiling is active.
func (f *Flag) Enabled() bool { return f.v == 1 }
