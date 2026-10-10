package debugger

import (
	"sync"
	"testing"
)

func TestBreakpointShouldBreak(t *testing.T) {
	bp := &Breakpoint{ID: 1, Node: "matmul", Enabled: true}
	if !bp.ShouldBreak("matmul", nil) {
		t.Error("expected break on match")
	}
	if bp.ShouldBreak("add", nil) {
		t.Error("should not break on other nodes")
	}
	if bp.Hits.Load() != 1 {
		t.Errorf("expected 1 hit, got %d", bp.Hits.Load())
	}
}

func TestBreakpointCondition(t *testing.T) {
	bp := &Breakpoint{Node: "mm", Enabled: true, Condition: func(v map[string]interface{}) bool {
		n, _ := v["step"].(int)
		return n == 3
	}}
	if bp.ShouldBreak("mm", map[string]interface{}{"step": 1}) {
		t.Error("condition should gate the break")
	}
	if !bp.ShouldBreak("mm", map[string]interface{}{"step": 3}) {
		t.Error("condition should allow the break")
	}
}

func TestBreakpointDisabled(t *testing.T) {
	bp := &Breakpoint{Node: "mm", Enabled: false}
	if bp.ShouldBreak("mm", nil) {
		t.Error("disabled breakpoint must never fire")
	}
}

func TestDebuggerBreakpointManagement(t *testing.T) {
	d := NewDebugger(16)
	bp := d.AddBreakpoint("a", nil)
	if len(d.Breakpoints()) != 1 {
		t.Fatal("breakpoint count")
	}
	if err := d.Enable(bp.ID, false); err != nil {
		t.Fatal(err)
	}
	if err := d.RemoveBreakpoint(bp.ID); err != nil {
		t.Fatal(err)
	}
	if len(d.Breakpoints()) != 0 {
		t.Error("expected removal")
	}
	if d.RemoveBreakpoint(999) == nil {
		t.Error("expected missing id error")
	}
	if d.Enable(999, true) == nil {
		t.Error("expected enable error for missing id")
	}
}

func TestDebuggerSession(t *testing.T) {
	d := NewDebugger(16)
	s := d.Start("run-1")
	if d.Session() != s {
		t.Error("session lookup")
	}
	d.SetVars(map[string]interface{}{"lr": 0.01})
	vars := d.Vars()
	if vars["lr"] != 0.01 {
		t.Errorf("vars: %v", vars)
	}
	d.Stop()
	if d.Session() != nil {
		t.Error("expected nil session after stop")
	}
	if d.Vars() != nil {
		t.Error("expected nil vars without a session")
	}
}

func TestDebuggerOnNode(t *testing.T) {
	d := NewDebugger(16)
	d.AddBreakpoint("mm", nil)
	s := d.Start("r")
	d.OnNode(s, "mm", nil)
	if d.Stats().Breaks.Load() != 1 {
		t.Error("expected a break")
	}
	if d.Stats().Steps.Load() != 1 {
		t.Error("expected a step")
	}
	// Without a session OnNode must be a no-op.
	d.OnNode(nil, "x", nil)
}

func TestDebuggerStep(t *testing.T) {
	d := NewDebugger(16)
	d.Start("r")
	err := d.Step("mm", func() (map[string]interface{}, error) {
		return map[string]interface{}{"out": 42}, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if got := d.Vars()["out"]; got != 42 {
		t.Errorf("expected captured vars, got %v", got)
	}
	if len(d.Trace()) != 1 {
		t.Fatal("trace length")
	}
	e := d.Trace()[0]
	if e.Node != "mm" {
		t.Errorf("trace node: %s", e.Node)
	}
}

func TestDebuggerStepNoSession(t *testing.T) {
	d := NewDebugger(16)
	if err := d.Step("mm", func() (map[string]interface{}, error) { return nil, nil }); err != ErrNoSession {
		t.Errorf("expected no session error, got %v", err)
	}
}

func TestDebuggerTraceFilters(t *testing.T) {
	d := NewDebugger(64)
	for i := 0; i < 3; i++ {
		d.Record(TraceEntry{Node: "a", DurUs: int64(i + 1)})
	}
	d.Record(TraceEntry{Node: "b", DurUs: 10})

	if got := d.TraceForNode("a"); len(got) != 3 {
		t.Errorf("expected 3, got %d", len(got))
	}
	if got := d.TraceForNode("zz"); len(got) != 0 {
		t.Error("expected no matches")
	}
	slow := d.Slowest(1)
	if len(slow) != 1 || slow[0].DurUs != 10 {
		t.Errorf("slowest: %+v", slow)
	}
}

func TestDebuggerTraceRetention(t *testing.T) {
	d := NewDebugger(2)
	for i := 0; i < 5; i++ {
		d.Record(TraceEntry{Node: "x"})
	}
	if len(d.Trace()) != 2 {
		t.Errorf("expected bounded trace of 2, got %d", len(d.Trace()))
	}
}

func TestDebuggerStepMode(t *testing.T) {
	d := NewDebugger(4)
	d.SetStepMode(StepEpoch)
	if d.StepMode() != StepEpoch {
		t.Error("step mode")
	}
	if StepEpoch.String() != "epoch" {
		t.Error("step kind string")
	}
}

func TestDebuggerTraceConcurrent(t *testing.T) {
	d := NewDebugger(1024)
	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 20; j++ {
				d.Record(TraceEntry{Node: "x"})
			}
		}()
	}
	wg.Wait()
	if len(d.Trace()) != 160 {
		t.Errorf("expected 160 entries, got %d", len(d.Trace()))
	}
}
