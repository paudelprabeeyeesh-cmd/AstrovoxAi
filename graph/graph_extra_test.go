package graph

import (
	"strings"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

func TestGraph_New(t *testing.T) {
	g := New("g1")
	if g.Name() != "g1" {
		t.Fatalf("name = %s, want g1", g.Name())
	}
}

func TestGraph_AddNode(t *testing.T) {
	g := New("g")
	op := OpFunc{OpName: "const", ShapeFn: shapeFn(2, 2), ForwardFn: fwdFn(1)}
	id, err := g.AddNode(op, nil)
	if err != nil {
		t.Fatalf("AddNode: %v", err)
	}
	if id != 0 {
		t.Fatalf("node id = %d, want 0", id)
	}
}

func TestGraph_AddNodeWithAttrs(t *testing.T) {
	g := New("g")
	op := OpFunc{OpName: "const", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)}
	id, err := g.AddNode(op, map[string]any{"key": "val"})
	if err != nil {
		t.Fatalf("AddNode: %v", err)
	}
	if id != 0 {
		t.Fatalf("id = %d, want 0", id)
	}
}

func TestGraph_NodeCount(t *testing.T) {
	g := New("g")
	if g.NodeCount() != 0 {
		t.Fatalf("node count = %d, want 0", g.NodeCount())
	}
	add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	if g.NodeCount() != 1 {
		t.Fatalf("node count = %d, want 1", g.NodeCount())
	}
}

func TestGraph_EdgeCount(t *testing.T) {
	g := New("g")
	if g.EdgeCount() != 0 {
		t.Fatalf("edge count = %d, want 0", g.EdgeCount())
	}
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	_, _ = g.AddEdge(n0, n1, 0, 0)
	if g.EdgeCount() != 1 {
		t.Fatalf("edge count = %d, want 1", g.EdgeCount())
	}
}

func TestGraph_Node(t *testing.T) {
	g := New("g")
	op := OpFunc{OpName: "const", ShapeFn: shapeFn(3), ForwardFn: fwdFn(5)}
	id := add(g, op)
	node, err := g.Node(id)
	if err != nil {
		t.Fatalf("Node: %v", err)
	}
	if node.Op.Name() != "const" {
		t.Fatalf("op name = %s, want const", node.Op.Name())
	}
}

func TestGraph_NodeMissing(t *testing.T) {
	g := New("g")
	if _, err := g.Node(99); err == nil {
		t.Fatal("expected error for missing node")
	}
}

func TestGraph_Nodes(t *testing.T) {
	g := New("g")
	add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	nodes := g.Nodes()
	if len(nodes) != 2 {
		t.Fatalf("nodes = %d, want 2", len(nodes))
	}
}

func TestGraph_Edges(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	_, _ = g.AddEdge(n0, n1, 0, 0)
	edges := g.Edges()
	if len(edges) != 1 {
		t.Fatalf("edges = %d, want 1", len(edges))
	}
}

func TestGraph_Adjacency(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	_, _ = g.AddEdge(n0, n1, 0, 0)
	adj := g.Adjacency()
	if len(adj[n0]) != 1 || adj[n0][0] != n1 {
		t.Fatalf("adjacency mismatch: %v", adj)
	}
}

func TestGraph_MarkOutput(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "out", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	if err := g.MarkOutput(n0); err != nil {
		t.Fatalf("MarkOutput: %v", err)
	}
	outs := g.Outputs()
	if len(outs) != 1 || outs[0] != n0 {
		t.Fatalf("outputs = %v, want [%d]", outs, n0)
	}
}

func TestGraph_MarkOutputMissing(t *testing.T) {
	g := New("g")
	if err := g.MarkOutput(99); err == nil {
		t.Fatal("expected error for missing output node")
	}
}

func TestGraph_HasCycle(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	_, _ = g.AddEdge(n0, n1, 0, 0)
	if g.HasCycle() {
		t.Fatal("expected no cycle")
	}
	_, _ = g.AddEdge(n1, n0, 0, 0)
	if !g.HasCycle() {
		t.Fatal("expected cycle after back edge")
	}
}

func TestGraph_Validate(t *testing.T) {
	g := New("g")
	if err := g.Validate(); err != nil {
		t.Fatalf("empty graph validate: %v", err)
	}
	_ = add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	if err := g.Validate(); err != nil {
		t.Fatalf("single node validate: %v", err)
	}
}

func TestGraph_Connect(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n2 := add(g, OpFunc{OpName: "c", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	if err := g.Connect([][2]int{{n0, n1}, {n1, n2}}); err != nil {
		t.Fatalf("Connect: %v", err)
	}
	if g.EdgeCount() != 2 {
		t.Fatalf("edges = %d, want 2", g.EdgeCount())
	}
}

func TestGraph_SelfLoop(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	if _, err := g.AddEdge(n0, n0, 0, 0); err == nil {
		t.Fatal("expected error for self-loop")
	}
}

func TestGraph_InvalidNode(t *testing.T) {
	g := New("g")
	if _, err := g.AddEdge(99, 100, 0, 0); err == nil {
		t.Fatal("expected error for invalid node")
	}
}

func TestGraph_MultipleOutputs(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "out1", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "out2", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	_ = g.MarkOutput(n0)
	_ = g.MarkOutput(n1)
	outs := g.Outputs()
	if len(outs) != 2 {
		t.Fatalf("outputs = %d, want 2", len(outs))
	}
}

func TestNode_OutShapes(t *testing.T) {
	g := New("g")
	op := OpFunc{OpName: "src", ShapeFn: shapeFn(4), ForwardFn: fwdFn(1)}
	n0 := add(g, op)
	node, _ := g.Node(n0)
	shapes := node.OutShapes()
	if len(shapes) != 1 {
		t.Fatalf("outshapes = %d, want 1", len(shapes))
	}
	if shapes[0].Rank() != 1 || shapes[0].Dims()[0] != 4 {
		t.Fatalf("shape = %v, want [4]", shapes[0].Dims())
	}
}

func TestEdge_Endpoints(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	eid, _ := g.AddEdge(n0, n1, 0, 0)
	e := g.edge(eid)
	from, to := e.Endpoints()
	if from != n0 || to != n1 {
		t.Fatalf("endpoints = (%d,%d), want (%d,%d)", from, to, n0, n1)
	}
}

func TestEdge_Target(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	eid, _ := g.AddEdge(n0, n1, 2, 3)
	e := g.edge(eid)
	to, port := e.Target()
	if to != n1 || port != 3 {
		t.Fatalf("target = (%d,%d), want (%d,%d)", to, port, n1, 3)
	}
}

func TestOpFunc_Name(t *testing.T) {
	op := OpFunc{OpName: "relu"}
	if op.Name() != "relu" {
		t.Fatalf("name = %s, want relu", op.Name())
	}
}

func TestOpFunc_InferShape(t *testing.T) {
	op := OpFunc{OpName: "reshape", ShapeFn: shapeFn(3, 3)}
	out, err := op.InferShape([]tensor.Shape{tensor.MustShape(9)})
	if err != nil {
		t.Fatalf("InferShape: %v", err)
	}
	if len(out) != 1 || out[0].Rank() != 2 || out[0].Dims()[0] != 3 {
		t.Fatalf("shape = %v, want [3,3]", out[0].Dims())
	}
}

func TestOpFunc_Forward(t *testing.T) {
	op := OpFunc{OpName: "fill", ShapeFn: shapeFn(2, 2), ForwardFn: fwdFn(7)}
	out, err := op.Forward(nil)
	if err != nil {
		t.Fatalf("Forward: %v", err)
	}
	if len(out) != 1 || out[0].NumElements() != 4 {
		t.Fatalf("output elements = %d, want 4", out[0].NumElements())
	}
}

func TestVisualizer_DOT(t *testing.T) {
	v := &Visualizer{}
	g := New("g")
	n0 := add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	_, _ = g.AddEdge(n0, n1, 0, 0)
	dot, err := v.DOT(g)
	if err != nil {
		t.Fatalf("DOT: %v", err)
	}
	if !strings.Contains(dot, "digraph") {
		t.Fatalf("dot missing digraph header: %s", dot)
	}
}

func TestVisualizer_WriteDOT(t *testing.T) {
	v := &Visualizer{}
	g := New("g")
	_ = add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	var buf strings.Builder
	if err := v.WriteDOT(g, &buf); err != nil {
		t.Fatalf("WriteDOT: %v", err)
	}
	if !strings.Contains(buf.String(), "digraph") {
		t.Fatal("expected digraph in output")
	}
}

func TestVisualizer_Summary(t *testing.T) {
	v := &Visualizer{}
	g := New("g")
	add(g, OpFunc{OpName: "a", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	add(g, OpFunc{OpName: "b", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	_, _ = g.AddEdge(0, 1, 0, 0)
	s, err := v.Summary(g)
	if err != nil {
		t.Fatalf("Summary: %v", err)
	}
	if s == "" {
		t.Fatal("expected non-empty summary")
	}
}

func TestOptimizer_Stats(t *testing.T) {
	o := NewOptimizer()
	p, r, f := o.Stats()
	if p != 0 || r != 0 || f != 0 {
		t.Fatalf("initial stats = (%d,%d,%d), want (0,0,0)", p, r, f)
	}
}

func TestOptimizer_StatsAfterRun(t *testing.T) {
	g := New("g")
	n0 := add(g, OpFunc{OpName: "src", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	n1 := add(g, OpFunc{OpName: "dead", ShapeFn: shapeFn(2), ForwardFn: fwdFn(1)})
	_, _ = g.AddEdge(n0, n1, 0, 0)
	_ = g.MarkOutput(n0)
	o := NewOptimizer()
	if err := o.Optimize(g); err != nil {
		t.Fatalf("Optimize: %v", err)
	}
	_, removed, fused := o.Stats()
	if removed < 0 || fused < 0 {
		t.Fatalf("negative stats: removed=%d fused=%d", removed, fused)
	}
}

func TestExecutor_SetProfiler(t *testing.T) {
	g := New("g")
	_, err := NewExecutor(g)
	if err != nil {
		t.Fatalf("NewExecutor: %v", err)
	}
}
