package tools

import "testing"

func TestGraphViewer_RenderDOT(t *testing.T) {
	v := NewGraphViewer()
	dot := v.RenderDOT([]string{"a", "b"}, [][2]string{{"a", "b"}})
	if !strings.Contains(dot, "digraph") {
		t.Fatal("expected digraph")
	}
	if !strings.Contains(dot, "a") || !strings.Contains(dot, "b") {
		t.Fatal("expected nodes")
	}
}

func TestGraphViewer_RenderEmpty(t *testing.T) {
	v := NewGraphViewer()
	dot := v.RenderDOT([]string{}, [][2]string{})
	if !strings.Contains(dot, "digraph") {
		t.Fatal("expected digraph")
	}
}

func TestTensorInspector_Stats(t *testing.T) {
	i := NewTensorInspector()
	stats := i.Stats([]float64{1, 2, 3})
	if stats["count"] != 3 {
		t.Errorf("count = %f, want 3", stats["count"])
	}
	if stats["min"] != 1 || stats["max"] != 3 {
		t.Errorf("min/max wrong: %v", stats)
	}
}

func TestTensorInspector_Empty(t *testing.T) {
	i := NewTensorInspector()
	stats := i.Stats([]float64{})
	if len(stats) != 0 {
		t.Fatalf("expected empty stats, got %v", stats)
	}
}

func TestMemoryProfiler_Peak(t *testing.T) {
	p := NewMemoryProfiler()
	p.RecordAllocation(10)
	p.RecordAllocation(20)
	p.RecordAllocation(-5)
	peak := p.Peak()
	if peak != 30 {
		t.Errorf("peak = %d, want 30", peak)
	}
}

func TestMemoryProfiler_Empty(t *testing.T) {
	p := NewMemoryProfiler()
	if peak := p.Peak(); peak != 0 {
		t.Errorf("expected 0 peak, got %d", peak)
	}
}

func TestBenchmarkDashboard_AddResult(t *testing.T) {
	d := NewBenchmarkDashboard()
	d.AddResult("test", 100.5)
	if len(d.Results) != 1 {
		t.Fatalf("expected 1 result")
	}
	if d.Results["test"] != 100.5 {
		t.Errorf("expected 100.5, got %f", d.Results["test"])
	}
}

func TestBenchmarkDashboard_Summary(t *testing.T) {
	d := NewBenchmarkDashboard()
	d.AddResult("test", 100.5)
	summary := d.Summary()
	if !strings.Contains(summary, "test") {
		t.Fatal("expected test in summary")
	}
	if !strings.Contains(summary, "100.50") {
		t.Fatal("expected 100.50 in summary")
	}
}

func TestDebugger_SetBreakpoint(t *testing.T) {
	d := NewDebugger()
	d.SetBreakpoint(1)
	if !d.Breakpoints[1] {
		t.Fatal("expected breakpoint set")
	}
}

func TestDebugger_Step(t *testing.T) {
	d := NewDebugger()
	d.Step()
	if d.Steps != 1 {
		t.Errorf("steps = %d, want 1", d.Steps)
	}
}

func TestTracer_StartEnd(t *testing.T) {
	tracer := NewTracer()
	span := tracer.Start("test")
	span.End(10)
	spans := tracer.SpansList()
	if len(spans) != 1 {
		t.Fatalf("expected 1 span")
	}
	if spans[0].Name != "test" {
		t.Fatalf("expected span name test")
	}
}

func TestTracer_MultipleSpans(t *testing.T) {
	tracer := NewTracer()
	tracer.Start("a")
	tracer.Start("b")
	spans := tracer.SpansList()
	if len(spans) != 2 {
		t.Fatalf("expected 2 spans, got %d", len(spans))
	}
}
