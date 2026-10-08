package tools

import (
	"strings"
	"testing"
)

func TestGraphViewer_RenderSingleNode(t *testing.T) {
	v := NewGraphViewer()
	dot := v.RenderDOT([]string{"n0"}, nil)
	if !strings.Contains(dot, `n0 [label="n0"]`) {
		t.Fatalf("missing node label: %s", dot)
	}
	if !strings.Contains(dot, "digraph astrovox") {
		t.Fatalf("missing header: %s", dot)
	}
}

func TestGraphViewer_RenderEdge(t *testing.T) {
	v := NewGraphViewer()
	dot := v.RenderDOT([]string{"a", "b"}, [][2]string{{"a", "b"}})
	if !strings.Contains(dot, "na -> nb") {
		t.Fatalf("missing edge: %s", dot)
	}
}

func TestGraphViewer_RenderMultiEdge(t *testing.T) {
	v := NewGraphViewer()
	dot := v.RenderDOT([]string{"a", "b", "c"}, [][2]string{{"a", "b"}, {"b", "c"}})
	if !strings.Contains(dot, "na -> nb") {
		t.Fatalf("missing first edge: %s", dot)
	}
	if !strings.Contains(dot, "nb -> nc") {
		t.Fatalf("missing second edge: %s", dot)
	}
}

func TestGraphViewer_DOTClosingBrace(t *testing.T) {
	v := NewGraphViewer()
	dot := v.RenderDOT([]string{"x"}, nil)
	if !strings.HasSuffix(strings.TrimSpace(dot), "}") {
		t.Fatalf("missing closing brace: %s", dot)
	}
}

func TestGraphViewer_Rankdir(t *testing.T) {
	v := NewGraphViewer()
	if !strings.Contains(v.RenderDOT(nil, nil), "rankdir=TB") {
		t.Fatal("missing rankdir=TB")
	}
}

func TestTensorInspector_SingleElement(t *testing.T) {
	i := NewTensorInspector()
	s := i.Stats([]float64{42})
	if s["count"] != 1 || s["min"] != 42 || s["max"] != 42 || s["mean"] != 42 {
		t.Fatalf("unexpected stats: %v", s)
	}
}

func TestTensorInspector_NegativeValues(t *testing.T) {
	i := NewTensorInspector()
	s := i.Stats([]float64{-5, -1, -10})
	if s["min"] != -10 || s["max"] != -1 {
		t.Fatalf("min/max = %v/%v, want -10/-1", s["min"], s["max"])
	}
}

func TestMemoryProfiler_SingleAllocation(t *testing.T) {
	p := NewMemoryProfiler()
	p.RecordAllocation(256)
	if p.Peak() != 256 {
		t.Fatalf("peak = %d, want 256", p.Peak())
	}
}

func TestBenchmarkDashboard_Empty(t *testing.T) {
	d := NewBenchmarkDashboard()
	if s := d.Summary(); s != "" {
		t.Fatalf("expected empty summary, got: %s", s)
	}
}

func TestBenchmarkDashboard_Overwrite(t *testing.T) {
	d := NewBenchmarkDashboard()
	d.AddResult("op1", 100)
	d.AddResult("op1", 200)
	if d.Results["op1"] != 200 {
		t.Fatalf("overwrite: got %v, want 200", d.Results["op1"])
	}
}

func TestDebugger_NewInitialized(t *testing.T) {
	d := NewDebugger()
	if d.Breakpoints == nil {
		t.Fatal("Breakpoints should be initialized")
	}
	if d.Steps != 0 {
		t.Fatalf("initial steps = %d, want 0", d.Steps)
	}
}

func TestTracer_SingleSpan(t *testing.T) {
	tracer := NewTracer()
	span := tracer.Start("op1")
	span.Complete(10)
	spans := tracer.SpansList()
	if len(spans) != 1 {
		t.Fatalf("spans = %d, want 1", len(spans))
	}
	if spans[0].Name != "op1" {
		t.Fatalf("name = %s, want op1", spans[0].Name)
	}
	if spans[0].Start != 1 {
		t.Fatalf("start = %d, want 1", spans[0].Start)
	}
	if span.End != 10 {
		t.Fatalf("span.End = %d, want 10 (returned pointer)", span.End)
	}
}

func TestTracer_SpansListCopy(t *testing.T) {
	tracer := NewTracer()
	tracer.Start("x").Complete(1)
	s1 := tracer.SpansList()
	tracer.Start("y").Complete(2)
	s2 := tracer.SpansList()
	if len(s1) != 1 || len(s2) != 2 {
		t.Fatalf("copy length: s1=%d s2=%d", len(s1), len(s2))
	}
}

func TestTracer_NewEmpty(t *testing.T) {
	tracer := NewTracer()
	if len(tracer.SpansList()) != 0 {
		t.Fatal("new tracer should have no spans")
	}
}

func TestSpan_Fields(t *testing.T) {
	s := Span{Name: "foo", Start: 1, End: 2}
	if s.Name != "foo" || s.Start != 1 || s.End != 2 {
		t.Fatalf("span fields = %+v", s)
	}
}

func TestSpan_Complete(t *testing.T) {
	var s Span
	s.Complete(99)
	if s.End != 99 {
		t.Fatalf("End = %d, want 99", s.End)
	}
}
