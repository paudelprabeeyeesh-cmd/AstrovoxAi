package tools

import (
	"bytes"
	"fmt"
)

// GraphViewer renders IR graphs as DOT.
type GraphViewer struct{}

// NewGraphViewer creates a new viewer.
func NewGraphViewer() *GraphViewer {
	return &GraphViewer{}
}

// RenderDOT renders a graph description to DOT.
func (v *GraphViewer) RenderDOT(nodes []string, edges [][2]string) string {
	var buf bytes.Buffer
	buf.WriteString("digraph astrovox {\n")
	buf.WriteString("  rankdir=TB;\n")
	for _, n := range nodes {
		buf.WriteString(fmt.Sprintf("  n%s [label=\"%s\"];\n", n, n))
	}
	for _, e := range edges {
		buf.WriteString(fmt.Sprintf("  n%s -> n%s;\n", e[0], e[1]))
	}
	buf.WriteString("}\n")
	return buf.String()
}

// TensorInspector inspects tensor properties.
type TensorInspector struct{}

// NewTensorInspector creates a new inspector.
func NewTensorInspector() *TensorInspector {
	return &TensorInspector{}
}

// Stats returns basic tensor statistics.
func (i *TensorInspector) Stats(data []float64) map[string]float64 {
	if len(data) == 0 {
		return map[string]float64{}
	}
	sum := 0.0
	min := data[0]
	max := data[0]
	for _, v := range data {
		sum += v
		if v < min {
			min = v
		}
		if v > max {
			max = v
		}
	}
	return map[string]float64{
		"count": float64(len(data)),
		"sum":   sum,
		"min":   min,
		"max":   max,
		"mean":  sum / float64(len(data)),
	}
}

// MemoryProfiler tracks allocation patterns.
type MemoryProfiler struct {
	allocations []int
}

// NewMemoryProfiler creates a new profiler.
func NewMemoryProfiler() *MemoryProfiler {
	return &MemoryProfiler{}
}

// RecordAllocation records a memory allocation.
func (p *MemoryProfiler) RecordAllocation(bytes int) {
	p.allocations = append(p.allocations, bytes)
}

// Peak returns the peak allocation observed.
func (p *MemoryProfiler) Peak() int {
	peak := 0
	current := 0
	for _, b := range p.allocations {
		current += b
		if current > peak {
			peak = current
		}
	}
	return peak
}

// BenchmarkDashboard summarizes benchmark results.
type BenchmarkDashboard struct {
	Results map[string]float64
}

// NewBenchmarkDashboard creates a new dashboard.
func NewBenchmarkDashboard() *BenchmarkDashboard {
	return &BenchmarkDashboard{Results: make(map[string]float64)}
}

// AddResult adds a benchmark result.
func (d *BenchmarkDashboard) AddResult(name string, nsPerOp float64) {
	d.Results[name] = nsPerOp
}

// Summary returns a summary string.
func (d *BenchmarkDashboard) Summary() string {
	var buf bytes.Buffer
	for name, ns := range d.Results {
		buf.WriteString(fmt.Sprintf("%s: %.2f ns/op\n", name, ns))
	}
	return buf.String()
}

// Debugger supports step execution tracing.
type Debugger struct {
	Breakpoints map[int]bool
	Steps       int
}

// NewDebugger creates a new debugger.
func NewDebugger() *Debugger {
	return &Debugger{Breakpoints: make(map[int]bool)}
}

// SetBreakpoint sets a breakpoint.
func (d *Debugger) SetBreakpoint(id int) {
	d.Breakpoints[id] = true
}

// Step advances one step.
func (d *Debugger) Step() {
	d.Steps++
}

// Tracer records execution spans.
type Tracer struct {
	Spans []Span
}

// Span represents a traced span.
type Span struct {
	Name  string
	Start int64
	End   int64
}

// NewTracer creates a new tracer.
func NewTracer() *Tracer {
	return &Tracer{}
}

// Start begins a span.
func (t *Tracer) Start(name string) *Span {
	span := &Span{Name: name, Start: 1}
	t.Spans = append(t.Spans, *span)
	return span
}

// Complete completes a span.
func (s *Span) Complete(end int64) {
	s.End = end
}

// Spans returns all recorded spans.
func (t *Tracer) SpansList() []Span {
	return append([]Span(nil), t.Spans...)
}
