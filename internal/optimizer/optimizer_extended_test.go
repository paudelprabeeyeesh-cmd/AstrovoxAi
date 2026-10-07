package optimizer_test

import (
	"testing"

	"github.com/astrovox/astrovox/internal/optimizer"
)

func TestOptimizerConstantFolding(t *testing.T) {
	g := optimizer.NewGraph()
	g.Constants["a"] = 2.0
	g.Constants["b"] = 3.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.Output = "c"
	g.ConstantFolding()
	n := g.Nodes["c"]
	if !n.Computed || n.Value != 5.0 {
		t.Fatalf("expected folded value, got %v", n.Value)
	}
}

func TestOptimizerDeadCodeElimination(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("dead", "constant", nil)
	g.AddNode("c", "add", []string{"a"})
	g.Output = "c"
	g.DeadCodeElimination()
	if _, ok := g.Nodes["dead"]; ok {
		t.Fatal("expected dead node removed")
	}
}

func TestOptimizerDeadCodeEliminationEmptyOutput(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.Output = ""
	g.DeadCodeElimination()
	if len(g.Nodes) != 0 {
		t.Fatalf("expected 0 nodes, got %d", len(g.Nodes))
	}
}

func TestOptimizerCommonSubexpressionElimination(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c1", "add", []string{"a", "b"})
	g.AddNode("c2", "add", []string{"a", "b"})
	g.Output = "c1"
	g.CommonSubexpressionElimination()
}

func TestOptimizerTopologicalSort(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	order := g.TopologicalSort()
	if len(order) != 3 {
		t.Fatalf("expected 3 nodes, got %d", len(order))
	}
}

func TestOptimizerInlineConstants(t *testing.T) {
	g := optimizer.NewGraph()
	g.Constants["a"] = 2.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "add", []string{"a"})
	g.Output = "b"
	g.ConstantFolding()
}

func TestOptimizerOperatorFusion(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "matmul", []string{"a"})
	g.AddNode("c", "add", []string{"b"})
	g.Output = "c"
	g.OperatorFusion()
}

func TestOptimizerEmptyGraph(t *testing.T) {
	g := optimizer.NewGraph()
	g.ConstantFolding()
	g.DeadCodeElimination()
	g.CommonSubexpressionElimination()
	g.OperatorFusion()
}

func TestOptimizerMultipleConstants(t *testing.T) {
	g := optimizer.NewGraph()
	g.Constants["a"] = 1.0
	g.Constants["b"] = 2.0
	g.Constants["c"] = 3.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "constant", nil)
	g.AddNode("d", "add", []string{"a", "b"})
	g.AddNode("e", "add", []string{"d", "c"})
	g.Output = "e"
	g.ConstantFolding()
	if !g.Nodes["e"].Computed || g.Nodes["e"].Value != 6.0 {
		t.Fatalf("expected 6.0, got %v", g.Nodes["e"].Value)
	}
}

func TestOptimizerNodeValue(t *testing.T) {
	g := optimizer.NewGraph()
	g.Constants["a"] = 3.0
	g.AddNode("a", "constant", nil)
	n := g.Nodes["a"]
	if n.Value != 3.0 {
		t.Fatalf("expected 3.0, got %v", n.Value)
	}
}
