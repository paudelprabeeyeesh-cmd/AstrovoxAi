package ir_test

import (
	"bytes"
	"encoding/json"
	"testing"

	"github.com/astrovox/astrovox/internal/ir"
)

func TestIRAddMultipleNodes(t *testing.T) {
	g := ir.NewGraph()
	id1 := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "const"})
	id2 := g.AddNode(&ir.Node{Kind: ir.NodeKindVariable, Op: "var"})
	if id1 == id2 {
		t.Fatal("expected unique ids")
	}
	if g.NodeCount() != 2 {
		t.Fatalf("expected 2 nodes, got %d", g.NodeCount())
	}
}

func TestIRMarshalEmpty(t *testing.T) {
	g := ir.NewGraph()
	b, err := g.MarshalJSON()
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	if !bytes.Contains(b, []byte("nodes")) {
		t.Fatal("expected nodes")
	}
}

func TestIRUnmarshalRoundTrip(t *testing.T) {
	g := ir.NewGraph()
	g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c"})
	b, _ := g.MarshalJSON()
	g2 := ir.NewGraph()
	if err := g2.UnmarshalJSON(b); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if g2.NodeCount() != 1 {
		t.Fatalf("expected 1 node")
	}
}

func TestIRWriteGraphviz(t *testing.T) {
	g := ir.NewGraph()
	g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c"})
	var buf bytes.Buffer
	if err := g.WriteGraphviz(&buf); err != nil {
		t.Fatalf("graphviz failed: %v", err)
	}
	if !bytes.Contains(buf.Bytes(), []byte("digraph")) {
		t.Fatal("expected digraph")
	}
}

func TestIRShapeString(t *testing.T) {
	var s ir.Shape
	if s.String() != "[]" {
		t.Fatalf("expected []")
	}
	s2 := ir.Shape{2, 3}
	if s2.String() != "[2x3]" {
		t.Fatalf("expected [2x3]")
	}
}

func TestIRShapeNumElements(t *testing.T) {
	s := ir.Shape{2, 3}
	if s.NumElements() != 6 {
		t.Fatalf("expected 6")
	}
	s2 := ir.Shape{-1, 3}
	if s2.NumElements() != -1 {
		t.Fatalf("expected -1")
	}
}

func TestIRNodeClone(t *testing.T) {
	g := ir.NewGraph()
	id := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c", Shape: ir.Shape{2}, DType: ir.DataTypeFloat32, Metadata: map[string]string{"key": "val"}})
	n := g.GetNode(id).Clone()
	if n == nil {
		t.Fatal("expected cloned node")
	}
	if n.Metadata["key"] != "val" {
		t.Fatalf("expected metadata preserved")
	}
}

func TestIRRemoveNode(t *testing.T) {
	g := ir.NewGraph()
	g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c"})
	if g.NodeCount() != 1 {
		t.Fatalf("expected 1 node")
	}
	for id := range g.Nodes {
		g.RemoveNode(id)
	}
	if g.NodeCount() != 0 {
		t.Fatalf("expected 0 nodes")
	}
}

func TestIRValidateGraph(t *testing.T) {
	g := ir.NewGraph()
	if err := g.ValidateGraph(); err != nil {
		t.Fatalf("empty graph should validate: %v", err)
	}
}

func TestIRTopologicalSort(t *testing.T) {
	g := ir.NewGraph()
	id1 := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "a"})
	id2 := g.AddNode(&ir.Node{Kind: ir.NodeKindCall, Op: "b", Inputs: []int64{id1}})
	order := g.TopologicalSort()
	if order[0].ID != id1 || order[1].ID != id2 {
		t.Fatal("unexpected order")
	}
}

func TestIRInferShape(t *testing.T) {
	g := ir.NewGraph()
	g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c", Attrs: map[string]interface{}{"value": []float64{1, 2, 3}}})
	if err := g.InferShape(); err != nil {
		t.Fatalf("infer shape failed: %v", err)
	}
}

func TestIRInferType(t *testing.T) {
	g := ir.NewGraph()
	g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c", Attrs: map[string]interface{}{"value": 3.14}})
	if err := g.InferType(); err != nil {
		t.Fatalf("infer type failed: %v", err)
	}
}

func TestIREnrichMetadata(t *testing.T) {
	g := ir.NewGraph()
	id := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c", Shape: ir.Shape{2, 3}, DType: ir.DataTypeFloat32})
	g.EnrichMetadata()
	n := g.GetNode(id)
	if n.Metadata["kind"] != "constant" {
		t.Fatalf("expected kind metadata")
	}
}

func TestIRGraphBuilder(t *testing.T) {
	b := ir.NewGraphBuilder()
	a := b.Constant("a", 1.0, ir.Shape{}, ir.DataTypeFloat64)
	b2 := b.Constant("b", 2.0, ir.Shape{}, ir.DataTypeFloat64)
	c := b.Call("add", []int64{a, b2}, ir.Shape{}, ir.DataTypeFloat64)
	b.SetOutput(c)
	g := b.Build()
	if g.NodeCount() != 3 {
		t.Fatalf("expected 3 nodes")
	}
}
