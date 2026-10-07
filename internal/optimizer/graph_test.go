package optimizer

import (
	"math"
	"testing"
)

func TestConstantFolding(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 2.0
	g.Constants["b"] = 3.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.Output = "c"
	g.ConstantFolding()
	c := g.Nodes["c"]
	if !c.Computed {
		t.Fatal("expected c to be computed")
	}
	if c.Value != 5.0 {
		t.Fatalf("expected 5.0, got %v", c.Value)
	}
}

func TestDeadCodeElimination(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.Output = "c"
	g.DeadCodeElimination()
	if _, ok := g.Nodes["a"]; !ok {
		t.Fatal("node 'a' should be kept")
	}
}

func TestCommonSubexpressionElimination(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c1", "add", []string{"a", "b"})
	g.AddNode("c2", "add", []string{"a", "b"})
	g.CommonSubexpressionElimination()
	if _, ok := g.Nodes["c2"]; ok {
		t.Fatal("expected c2 to be removed")
	}
}

func TestMemoryReusePlanning(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.Output = "c"
	reuse := g.MemoryReusePlanning()
	if reuse == nil {
		t.Fatal("expected reuse map")
	}
}

func TestOperatorFusion(t *testing.T) {
	g := NewGraph()
	g.AddNode("bias", "constant", nil)
	g.AddNode("mm", "matmul", []string{"a", "b"})
	g.AddNode("add", "add", []string{"mm", "bias"})
	g.Output = "add"
	g.OperatorFusion()
	mm := g.Nodes["mm"]
	if mm.Op != "fused_matmul_add" {
		t.Fatalf("expected fused_matmul_add, got %s", mm.Op)
	}
}

func TestTopologicalSort(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	order := g.TopologicalSort()
	if len(order) != 3 {
		t.Fatalf("expected 3 nodes, got %d", len(order))
	}
}

func TestEvaluateOperations(t *testing.T) {
	tests := []struct {
		op       string
		inputs   []float64
		expected float64
		ok       bool
	}{
		{"add", []float64{1, 2}, 3, true},
		{"mul", []float64{2, 3}, 6, true},
		{"sub", []float64{5, 2}, 3, true},
		{"div", []float64{6, 2}, 3, true},
		{"neg", []float64{5}, -5, true},
		{"relu", []float64{-1}, 0, true},
		{"sigmoid", []float64{0}, 0.5, true},
		{"exp", []float64{0}, 1, true},
		{"log", []float64{1}, 0, true},
		{"sqrt", []float64{4}, 2, true},
		{"pow", []float64{2, 3}, 8, true},
		{"unknown", []float64{1}, 0, false},
	}
	for _, tt := range tests {
		got, ok := evaluate(tt.op, tt.inputs)
		if ok != tt.ok {
			t.Errorf("evaluate(%v) ok = %v, want %v", tt.op, ok, tt.ok)
		}
		if ok && math.Abs(got-tt.expected) > 1e-9 {
			t.Errorf("evaluate(%v, %v) = %v, want %v", tt.op, tt.inputs, got, tt.expected)
		}
	}
}
