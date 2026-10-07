package optimizer

import (
	"math"
	"testing"
)

func TestGraphAddNode(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	if _, ok := g.Nodes["a"]; !ok {
		t.Fatal("expected node 'a' to exist")
	}
}

func TestConstantFoldingAdd(t *testing.T) {
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

func TestConstantFoldingMul(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 3.0
	g.Constants["b"] = 4.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "mul", []string{"a", "b"})
	g.Output = "c"
	g.ConstantFolding()
	c := g.Nodes["c"]
	if !c.Computed {
		t.Fatal("expected c to be computed")
	}
	if c.Value != 12.0 {
		t.Fatalf("expected 12.0, got %v", c.Value)
	}
}

func TestConstantFoldingSub(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 5.0
	g.Constants["b"] = 2.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "sub", []string{"a", "b"})
	g.Output = "c"
	g.ConstantFolding()
	c := g.Nodes["c"]
	if !c.Computed {
		t.Fatal("expected c to be computed")
	}
	if c.Value != 3.0 {
		t.Fatalf("expected 3.0, got %v", c.Value)
	}
}

func TestConstantFoldingDiv(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 6.0
	g.Constants["b"] = 2.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "div", []string{"a", "b"})
	g.Output = "c"
	g.ConstantFolding()
	c := g.Nodes["c"]
	if !c.Computed {
		t.Fatal("expected c to be computed")
	}
	if c.Value != 3.0 {
		t.Fatalf("expected 3.0, got %v", c.Value)
	}
}

func TestConstantFoldingNeg(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 5.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "neg", []string{"a"})
	g.Output = "b"
	g.ConstantFolding()
	b := g.Nodes["b"]
	if !b.Computed {
		t.Fatal("expected b to be computed")
	}
	if b.Value != -5.0 {
		t.Fatalf("expected -5.0, got %v", b.Value)
	}
}

func TestConstantFoldingRelu(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = -3.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "relu", []string{"a"})
	g.Output = "b"
	g.ConstantFolding()
	b := g.Nodes["b"]
	if !b.Computed {
		t.Fatal("expected b to be computed")
	}
	if b.Value != 0.0 {
		t.Fatalf("expected 0.0, got %v", b.Value)
	}
}

func TestConstantFoldingSigmoid(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 0.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "sigmoid", []string{"a"})
	g.Output = "b"
	g.ConstantFolding()
	b := g.Nodes["b"]
	if !b.Computed {
		t.Fatal("expected b to be computed")
	}
	if math.Abs(b.Value-0.5) > 1e-9 {
		t.Fatalf("expected 0.5, got %v", b.Value)
	}
}

func TestConstantFoldingExp(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 0.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "exp", []string{"a"})
	g.Output = "b"
	g.ConstantFolding()
	b := g.Nodes["b"]
	if !b.Computed {
		t.Fatal("expected b to be computed")
	}
	if math.Abs(b.Value-1.0) > 1e-9 {
		t.Fatalf("expected 1.0, got %v", b.Value)
	}
}

func TestConstantFoldingLog(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 1.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "log", []string{"a"})
	g.Output = "b"
	g.ConstantFolding()
	b := g.Nodes["b"]
	if !b.Computed {
		t.Fatal("expected b to be computed")
	}
	if math.Abs(b.Value-0.0) > 1e-9 {
		t.Fatalf("expected 0.0, got %v", b.Value)
	}
}

func TestConstantFoldingSqrt(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 4.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "sqrt", []string{"a"})
	g.Output = "b"
	g.ConstantFolding()
	b := g.Nodes["b"]
	if !b.Computed {
		t.Fatal("expected b to be computed")
	}
	if math.Abs(b.Value-2.0) > 1e-9 {
		t.Fatalf("expected 2.0, got %v", b.Value)
	}
}

func TestConstantFoldingPow(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 2.0
	g.Constants["b"] = 3.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "pow", []string{"a", "b"})
	g.Output = "c"
	g.ConstantFolding()
	c := g.Nodes["c"]
	if !c.Computed {
		t.Fatal("expected c to be computed")
	}
	if c.Value != 8.0 {
		t.Fatalf("expected 8.0, got %v", c.Value)
	}
}

func TestConstantFoldingNonConstantInputs(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "variable", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.Output = "c"
	g.ConstantFolding()
	c := g.Nodes["c"]
	if c.Computed {
		t.Fatal("expected c to not be computed")
	}
}

func TestDeadCodeEliminationRemovesUnreachable(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.Output = "c"
	g.DeadCodeElimination()
	if _, ok := g.Nodes["a"]; !ok {
		t.Fatal("node 'a' should be kept")
	}
	if _, ok := g.Nodes["b"]; !ok {
		t.Fatal("node 'b' should be kept")
	}
	if _, ok := g.Nodes["c"]; !ok {
		t.Fatal("node 'c' should be kept")
	}
}

func TestDeadCodeEliminationRemovesDead(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("dead", "constant", nil)
	g.AddNode("c", "add", []string{"a"})
	g.Output = "c"
	g.DeadCodeElimination()
	if _, ok := g.Nodes["dead"]; ok {
		t.Fatal("node 'dead' should be removed")
	}
}

func TestDeadCodeEliminationEmptyOutput(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.Output = ""
	g.DeadCodeElimination()
	if len(g.Nodes) != 0 {
		t.Fatalf("expected 0 nodes, got %d", len(g.Nodes))
	}
}

func TestCommonSubexpressionEliminationRemovesDuplicate(t *testing.T) {
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

func TestCommonSubexpressionEliminationKeepsDistinct(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c1", "add", []string{"a", "b"})
	g.AddNode("c2", "mul", []string{"a", "b"})
	g.CommonSubexpressionElimination()
	if _, ok := g.Nodes["c1"]; !ok {
		t.Fatal("c1 should be kept")
	}
	if _, ok := g.Nodes["c2"]; !ok {
		t.Fatal("c2 should be kept")
	}
}

func TestOperatorFusionMatMulBias(t *testing.T) {
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

func TestOperatorFusionNoFusion(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.Output = "c"
	g.OperatorFusion()
	c := g.Nodes["c"]
	if c.Op != "add" {
		t.Fatalf("expected add, got %s", c.Op)
	}
}

func TestTopologicalSortOrder(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	order := g.TopologicalSort()
	if len(order) != 3 {
		t.Fatalf("expected 3 nodes, got %d", len(order))
	}
	// a and b should come before c
	aIdx, bIdx, cIdx := -1, -1, -1
	for i, n := range order {
		switch n.Name {
		case "a":
			aIdx = i
		case "b":
			bIdx = i
		case "c":
			cIdx = i
		}
	}
	if aIdx > cIdx || bIdx > cIdx {
		t.Fatal("topological order violated: dependencies should come before dependents")
	}
}

func TestTopologicalSortComplex(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.AddNode("d", "add", []string{"c", "b"})
	order := g.TopologicalSort()
	if len(order) != 4 {
		t.Fatalf("expected 4 nodes, got %d", len(order))
	}
}

func TestMemoryReusePlanningExtended(t *testing.T) {
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

func TestSimplifyRunsAllPasses(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 1.0
	g.Constants["b"] = 2.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.AddNode("d", "add", []string{"c", "b"})
	g.Output = "d"
	g.Simplify()
	if len(g.Nodes) == 0 {
		t.Fatal("expected some nodes to remain after simplify")
	}
}

func TestSortTopological(t *testing.T) {
	g := NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	names := g.SortTopological()
	if len(names) != 3 {
		t.Fatalf("expected 3 names, got %d", len(names))
	}
}

func TestEvaluateOperationsTable(t *testing.T) {
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

func TestAllInputsComputed(t *testing.T) {
	nodes := map[string]*Node{
		"a": {Name: "a", Op: "constant", Computed: true},
		"b": {Name: "b", Op: "constant", Computed: true},
	}
	if !allInputsComputed([]string{"a", "b"}, nodes) {
		t.Fatal("expected all inputs to be computed")
	}
	if allInputsComputed([]string{"a", "c"}, nodes) {
		t.Fatal("expected not all inputs to be computed")
	}
}

func TestNodeValue(t *testing.T) {
	g := NewGraph()
	g.Constants["a"] = 3.0
	g.AddNode("a", "constant", nil)
	n := g.Nodes["a"]
	if n.Value != 3.0 {
		t.Fatalf("expected 3.0, got %v", n.Value)
	}
}
