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
	kinds := []NodeKind{NodeKindConstant, NodeKindVariable, NodeKindFunction, NodeKindLoop, NodeKindBranch, NodeKindReturn, NodeKindCall}
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
	types := []DataType{DataTypeFloat32, DataTypeFloat64, DataTypeInt32, DataTypeInt64, DataTypeBool}
	for _, dt := range types {
		n := &Node{Kind: NodeKindConstant, Op: "const", DType: dt}
		if n.DType != dt {
			t.Fatalf("expected dtype %s, got %s", dt, n.DType)
		}
	}
}
