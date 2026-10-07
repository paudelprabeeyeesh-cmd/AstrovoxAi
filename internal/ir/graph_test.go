package ir

import (
	"bytes"
	"testing"
)

func TestGraphAddMultipleNodes(t *testing.T) {
	g := NewGraph()
	id1 := g.AddNode(&Node{Kind: NodeKindConstant, Op: "const", Attrs: map[string]interface{}{"value": 1.0}})
	id2 := g.AddNode(&Node{Kind: NodeKindVariable, Op: "var", Attrs: map[string]interface{}{"name": "x"}})
	if id1 == id2 {
		t.Fatal("expected unique node ids")
	}
	if len(g.Nodes) != 2 {
		t.Fatalf("expected 2 nodes, got %d", len(g.Nodes))
	}
}

func TestGraphNodeKinds(t *testing.T) {
	kinds := []NodeKind{NodeKindConstant, NodeKindVariable, NodeKindFunction, NodeKindLoop, NodeKindBranch, NodeKindReturn, NodeKindCall, NodeKindPhi, NodeKindSwitch, NodeKindAlloca, NodeKindLoad, NodeKindStore}
	for _, kind := range kinds {
		n := &Node{Kind: kind, Op: "test"}
		if n.Kind != kind {
			t.Fatalf("expected kind %s, got %s", kind, n.Kind)
		}
	}
}

func TestGraphShapeAndDtype(t *testing.T) {
	g := NewGraph()
	shape := Shape{2, 3}
	id := g.AddNode(&Node{Kind: NodeKindConstant, Op: "const", Shape: shape, DType: DataTypeFloat32})
	n := g.Nodes[id]
	if len(n.Shape) != 2 {
		t.Fatalf("expected shape length 2, got %d", len(n.Shape))
	}
	if n.DType != DataTypeFloat32 {
		t.Fatalf("expected dtype float32, got %s", n.DType)
	}
}

func TestGraphMarshalEmpty(t *testing.T) {
	g := NewGraph()
	b, err := g.MarshalJSON()
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	if !bytes.Contains(b, []byte("nodes")) {
		t.Fatal("expected 'nodes' in JSON")
	}
}

func TestGraphUnmarshalRoundTrip(t *testing.T) {
	ResetIDCounter()
	g := NewGraph()
	id1 := g.AddNode(&Node{Kind: NodeKindConstant, Op: "const", Shape: Shape{2, 3}, DType: DataTypeFloat32})
	g.AddNode(&Node{Kind: NodeKindVariable, Op: "var", Inputs: []int64{id1}})
	g.Output = []int64{id1 + 1}
	b, err := g.MarshalJSON()
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	ResetIDCounter()
	g2 := NewGraph()
	if err := g2.UnmarshalJSON(b); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if g2.NodeCount() != 2 {
		t.Fatalf("expected 2 nodes, got %d", g2.NodeCount())
	}
	if len(g2.Output) != 1 || g2.Output[0] != id1+1 {
		t.Fatalf("expected output [%d], got %v", id1+1, g2.Output)
	}
	n := g2.GetNode(id1 + 1)
	if n == nil || n.Op != "var" {
		t.Fatalf("expected node %d to be 'var', got %v", id1+1, n)
	}
}

func TestGraphWriteGraphvizEmpty(t *testing.T) {
	g := NewGraph()
	var buf bytes.Buffer
	if err := g.WriteGraphviz(&buf); err != nil {
		t.Fatalf("graphviz write failed: %v", err)
	}
	if !bytes.Contains(buf.Bytes(), []byte("digraph")) {
		t.Fatal("expected digraph output")
	}
}

func TestGraphWriteGraphvizWithNodes(t *testing.T) {
	g := NewGraph()
	g.AddNode(&Node{Kind: NodeKindConstant, Op: "const"})
	g.AddNode(&Node{Kind: NodeKindVariable, Op: "var", Inputs: []int64{1}})
	var buf bytes.Buffer
	if err := g.WriteGraphviz(&buf); err != nil {
		t.Fatalf("graphviz write failed: %v", err)
	}
	if !bytes.Contains(buf.Bytes(), []byte("const")) {
		t.Fatal("expected 'const' in graphviz output")
	}
	if !bytes.Contains(buf.Bytes(), []byte("fillcolor")) {
		t.Fatal("expected colored nodes in graphviz output")
	}
}

func TestGraphReuseID(t *testing.T) {
	g := NewGraph()
	n := &Node{Kind: NodeKindConstant, Op: "const", ID: 42}
	id := g.AddNode(n)
	if id != 42 {
		t.Fatalf("expected id 42, got %d", id)
	}
}

func TestGraphDataTypes(t *testing.T) {
	types := []DataType{DataTypeFloat32, DataTypeFloat64, DataTypeInt32, DataTypeInt64, DataTypeBool, DataTypeUint8}
	for _, dt := range types {
		n := &Node{Kind: NodeKindConstant, Op: "const", DType: dt}
		if n.DType != dt {
			t.Fatalf("expected dtype %s, got %s", dt, n.DType)
		}
	}
}

func TestGraphClone(t *testing.T) {
	ResetIDCounter()
	g := NewGraph()
	id := g.AddNode(&Node{Kind: NodeKindConstant, Op: "const", Shape: Shape{2}, DType: DataTypeFloat32, Attrs: map[string]interface{}{"value": []float64{1.0, 2.0}}, Metadata: map[string]string{"key": "val"}})
	n := g.GetNode(id).Clone()
	if n == nil {
		t.Fatal("expected cloned node")
	}
	if n.ID != id {
		t.Fatalf("expected id %d, got %d", id, n.ID)
	}
	if n.Metadata["key"] != "val" {
		t.Fatalf("expected metadata preserved")
	}
	origSlice := g.Nodes[id].Attrs["value"].([]float64)
	cloneSlice := n.Attrs["value"].([]float64)
	if len(origSlice) != len(cloneSlice) || origSlice[0] != cloneSlice[0] || origSlice[1] != cloneSlice[1] {
		t.Fatal("expected slice attr values preserved")
	}
}

func TestGraphRemoveNode(t *testing.T) {
	g := NewGraph()
	g.AddNode(&Node{Kind: NodeKindConstant, Op: "const"})
	if g.NodeCount() != 1 {
		t.Fatalf("expected 1 node, got %d", g.NodeCount())
	}
	for id := range g.Nodes {
		g.RemoveNode(id)
	}
	if g.NodeCount() != 0 {
		t.Fatalf("expected 0 nodes, got %d", g.NodeCount())
	}
}

func TestGraphValidateGraph(t *testing.T) {
	g := NewGraph()
	if err := g.ValidateGraph(); err != nil {
		t.Fatalf("empty graph should validate: %v", err)
	}
	g.AddNode(&Node{Kind: NodeKindConstant, Op: "const", Inputs: []int64{999}})
	if err := g.ValidateGraph(); err == nil {
		t.Fatal("expected validation error for missing input")
	}
	g2 := NewGraph()
	id1 := g2.AddNode(&Node{Kind: NodeKindConstant, Op: "const"})
	id2 := g2.AddNode(&Node{Kind: NodeKindCall, Op: "add", Inputs: []int64{id1}})
	g2.Output = []int64{id2}
	if err := g2.ValidateGraph(); err != nil {
		t.Fatalf("valid graph should not error: %v", err)
	}
}

func TestGraphTopologicalSort(t *testing.T) {
	g := NewGraph()
	id1 := g.AddNode(&Node{Kind: NodeKindConstant, Op: "a"})
	id2 := g.AddNode(&Node{Kind: NodeKindConstant, Op: "b"})
	id3 := g.AddNode(&Node{Kind: NodeKindCall, Op: "add", Inputs: []int64{id1, id2}})
	order := g.TopologicalSort()
	if len(order) != 3 {
		t.Fatalf("expected 3 nodes, got %d", len(order))
	}
	if order[2].ID != id3 {
		t.Fatalf("expected last node to be add, got %d", order[2].ID)
	}
}

func TestGraphInferShape(t *testing.T) {
	g := NewGraph()
	id := g.AddNode(&Node{Kind: NodeKindConstant, Op: "const", Attrs: map[string]interface{}{"value": []float64{1, 2, 3}}})
	if err := g.InferShape(); err != nil {
		t.Fatalf("infer shape failed: %v", err)
	}
	if len(g.Nodes[id].Shape) != 1 || g.Nodes[id].Shape[0] != 3 {
		t.Fatalf("expected shape [3], got %v", g.Nodes[id].Shape)
	}
}

func TestGraphInferType(t *testing.T) {
	g := NewGraph()
	id := g.AddNode(&Node{Kind: NodeKindConstant, Op: "const", Attrs: map[string]interface{}{"value": 3.14}})
	if err := g.InferType(); err != nil {
		t.Fatalf("infer type failed: %v", err)
	}
	if g.Nodes[id].DType != DataTypeFloat64 {
		t.Fatalf("expected float64, got %s", g.Nodes[id].DType)
	}
}

func TestGraphEnrichMetadata(t *testing.T) {
	g := NewGraph()
	id := g.AddNode(&Node{Kind: NodeKindConstant, Op: "const", Shape: Shape{2, 3}, DType: DataTypeFloat32})
	g.EnrichMetadata()
	n := g.Nodes[id]
	if n.Metadata["kind"] != "constant" {
		t.Fatalf("expected kind metadata, got %v", n.Metadata["kind"])
	}
	if n.Metadata["shape"] != "[2x3]" {
		t.Fatalf("expected shape metadata, got %v", n.Metadata["shape"])
	}
	if n.Metadata["dtype"] != "float32" {
		t.Fatalf("expected dtype metadata, got %v", n.Metadata["dtype"])
	}
}

func TestGraphBuilder(t *testing.T) {
	b := NewGraphBuilder()
	a := b.Constant("a", 1.0, Shape{}, DataTypeFloat64)
	b2 := b.Constant("b", 2.0, Shape{}, DataTypeFloat64)
	c := b.Call("add", []int64{a, b2}, Shape{}, DataTypeFloat64)
	b.SetOutput(c)
	g := b.Build()
	if g.NodeCount() != 3 {
		t.Fatalf("expected 3 nodes, got %d", g.NodeCount())
	}
	if len(g.Output) != 1 || g.Output[0] != c {
		t.Fatalf("expected output %d, got %v", c, g.Output)
	}
}

func TestShapeString(t *testing.T) {
	var empty Shape
	if empty.String() != "[]" {
		t.Fatalf("expected []")
	}
	s := Shape{2, 3}
	if s.String() != "[2x3]" {
		t.Fatalf("expected [2x3]")
	}
	s2 := Shape{-1, 3}
	if s2.String() != "[?x3]" {
		t.Fatalf("expected [?x3]")
	}
}

func TestShapeNumElements(t *testing.T) {
	s := Shape{2, 3}
	if s.NumElements() != 6 {
		t.Fatalf("expected 6")
	}
	var empty Shape
	if empty.NumElements() != 1 {
		t.Fatalf("expected 1 for scalar")
	}
	s2 := Shape{-1, 3}
	if s2.NumElements() != -1 {
		t.Fatalf("expected -1 for unknown")
	}
}

func TestGraphCycleDetection(t *testing.T) {
	g := NewGraph()
	id1 := g.AddNode(&Node{Kind: NodeKindCall, Op: "a"})
	id2 := g.AddNode(&Node{Kind: NodeKindCall, Op: "b", Inputs: []int64{id1}})
	g.Nodes[id1].Inputs = []int64{id2}
	if err := g.ValidateGraph(); err == nil {
		t.Fatal("expected cycle detection error")
	}
}

