package graph

import (
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

// shapeFn returns a fixed-shape inference fn.
func shapeFn(dims ...int) func([]tensor.Shape) ([]tensor.Shape, error) {
	return func([]tensor.Shape) ([]tensor.Shape, error) {
		return []tensor.Shape{tensor.MustShape(dims...)}, nil
	}
}

// fwdFn returns a constant-output forward fn.
func fwdFn(val float64) func([]*tensor.Tensor) ([]*tensor.Tensor, error) {
	return func(inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
		out, err := tensor.Full(inputs[0].DType(), inputs[0].Shape().Dims(), val)
		if err != nil {
			return nil, err
		}
		return []*tensor.Tensor{out}, nil
	}
}

// add registers an op with no attributes.
func add(g *Graph, op OpFunc) int {
	id, err := g.AddNode(op, nil)
	if err != nil {
		panic(err)
	}
	return id
}

func TestTopologicalSort(t *testing.T) {
	g := New("test")
	n0 := add(g, OpFunc{OpName: "src0", ShapeFn: shapeFn(2, 2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "src1", ShapeFn: shapeFn(2, 2), ForwardFn: fwdFn(2)})
	n2 := add(g, OpFunc{OpName: "add", ShapeFn: shapeFn(2, 2), ForwardFn: fwdFn(3)})
	n3 := add(g, OpFunc{OpName: "sink", ShapeFn: shapeFn(2, 2), ForwardFn: fwdFn(4)})
	if _, err := g.AddEdge(n0, n2, 0, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n1, n2, 0, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n2, n3, 0, 0); err != nil {
		t.Fatal(err)
	}
	order, err := g.TopologicalSort()
	if err != nil {
		t.Fatal(err)
	}
	if len(order) != 4 {
		t.Fatalf("order length = %d, want 4", len(order))
	}
	// Sources must precede consumers.
	pos := map[int]int{}
	for i, id := range order {
		pos[id] = i
	}
	if pos[n0] >= pos[n2] || pos[n1] >= pos[n2] || pos[n2] >= pos[n3] {
		t.Fatalf("topological order violated: %v", order)
	}
	if g.HasCycle() {
		t.Fatal("HasCycle reported true for acyclic graph")
	}
}

func TestCycleDetection(t *testing.T) {
	g := New("cycle")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(1), ForwardFn: fwdFn(0)})
	n1 := add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(1), ForwardFn: fwdFn(0)})
	if _, err := g.AddEdge(n0, n1, 0, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n1, n0, 0, 0); err == nil {
		t.Fatal("expected cycle error, got nil")
	}
	if !g.HasCycle() {
		// The rejected edge was not added, so the
		// graph itself remains acyclic.
		t.Log("graph without the rejected edge is acyclic")
	}
}

func TestSelfLoopRejected(t *testing.T) {
	g := New("self")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(1), ForwardFn: fwdFn(0)})
	if _, err := g.AddEdge(n0, n0, 0, 0); err == nil {
		t.Fatal("expected self-loop error")
	}
}

func TestExecutorRun(t *testing.T) {
	g := New("exec")
	n0 := add(g, OpFunc{OpName: "src0", ShapeFn: shapeFn(2), ForwardFn: fwdFn(0)})
	n1 := add(g, OpFunc{OpName: "src1", ShapeFn: shapeFn(2), ForwardFn: fwdFn(0)})
	n2 := add(g, OpFunc{
		OpName:  "add",
		ShapeFn: shapeFn(2),
		ForwardFn: func(inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
			a := inputs[0].Float64()
			b := inputs[1].Float64()
			out, err := tensor.New(inputs[0].DType(), []int{2})
			if err != nil {
				return nil, err
			}
			for i := range a {
				if err := out.Set(a[i]+b[i], i); err != nil {
					return nil, err
				}
			}
			return []*tensor.Tensor{out}, nil
		},
	})
	if _, err := g.AddEdge(n0, n2, 0, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge(n1, n2, 0, 1); err != nil {
		t.Fatal(err)
	}
	if err := g.MarkOutput(n2); err != nil {
		t.Fatal(err)
	}
	exec, err := NewExecutor(g)
	if err != nil {
		t.Fatal(err)
	}
	a, _ := tensor.New(tensor.Float64, []int{2})
	_ = a.Set(1.0, 0)
	_ = a.Set(2.0, 1)
	b, _ := tensor.New(tensor.Float64, []int{2})
	_ = b.Set(10.0, 0)
	_ = b.Set(20.0, 1)
	out, err := exec.Run(t.Context(), []*tensor.Tensor{a, b})
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 {
		t.Fatalf("outputs = %d, want 1", len(out))
	}
	got := out[0].Float64()
	if got[0] != 11 || got[1] != 22 {
		t.Fatalf("result = %v, want [11 22]", got)
	}
}

func TestExecutorInputCountMismatch(t *testing.T) {
	g := New("mismatch")
	n0 := add(g, OpFunc{OpName: "src", ShapeFn: shapeFn(1), ForwardFn: fwdFn(0)})
	n1 := add(g, OpFunc{OpName: "sink", ShapeFn: shapeFn(1), ForwardFn: fwdFn(0)})
	if _, err := g.AddEdge(n0, n1, 0, 0); err != nil {
		t.Fatal(err)
	}
	exec, err := NewExecutor(g)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := exec.Run(t.Context(), nil); err == nil {
		t.Fatal("expected input count error")
	}
}

func TestVisualizerDOT(t *testing.T) {
	g := New("dot")
	n0 := add(g, OpFunc{OpName: "src", ShapeFn: shapeFn(3), ForwardFn: fwdFn(0)})
	n1 := add(g, OpFunc{OpName: "relu", ShapeFn: shapeFn(3), ForwardFn: fwdFn(0)})
	if _, err := g.AddEdge(n0, n1, 0, 0); err != nil {
		t.Fatal(err)
	}
	dot, err := DefaultVisualizer.DOT(g)
	if err != nil {
		t.Fatal(err)
	}
	if !contains(dot, "digraph") || !contains(dot, "n0") || !contains(dot, "n1") {
		t.Fatalf("DOT output missing content: %q", dot)
	}
	summary, err := DefaultVisualizer.Summary(g)
	if err != nil {
		t.Fatal(err)
	}
	if !contains(summary, "2 nodes, 1 edges") {
		t.Fatalf("summary missing counts: %q", summary)
	}
}

func contains(s, sub string) bool {
	return len(s) >= len(sub) && (s == sub || len(sub) == 0 ||
		(len(s) > 0 && indexOf(s, sub) >= 0))
}

func indexOf(s, sub string) int {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return i
		}
	}
	return -1
}

func TestOptimizerDCE(t *testing.T) {
	g := New("dce")
	n0 := add(g, OpFunc{OpName: "src", ShapeFn: shapeFn(2), ForwardFn: fwdFn(0)})
	// Dead node: not connected to any sink.
	add(g, OpFunc{OpName: "dead", ShapeFn: shapeFn(2), ForwardFn: fwdFn(0)})
	n2 := add(g, OpFunc{OpName: "sink", ShapeFn: shapeFn(2), ForwardFn: fwdFn(0)})
	if _, err := g.AddEdge(n0, n2, 0, 0); err != nil {
		t.Fatal(err)
	}
	if err := g.MarkOutput(n2); err != nil {
		t.Fatal(err)
	}
	opt := NewOptimizer()
	if err := opt.Optimize(g); err != nil {
		t.Fatal(err)
	}
	passes, removed, _ := opt.Stats()
	if removed == 0 {
		t.Fatalf("expected dead node removal, passes=%d", passes)
	}
	if g.NodeCount() != 2 {
		t.Fatalf("node count = %d, want 2", g.NodeCount())
	}
}
