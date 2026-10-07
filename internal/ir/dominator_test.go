package ir

import (
	"fmt"
	"testing"
)

func TestComputeDominatorsEmpty(t *testing.T) {
	dom := ComputeDominators(NewCFG())
	if dom == nil || len(dom.IDom) != 0 {
		t.Fatal("expected empty dominators")
	}
}

func TestComputeDominatorsSingleBlock(t *testing.T) {
	cfg := NewCFG()
	cfg.Entry = 1
	cfg.AddNode(&CFGNode{ID: 1, Label: "entry"})
	dom := ComputeDominators(cfg)
	if dom.IDom[1] != 1 {
		t.Fatalf("expected self idom, got %d", dom.IDom[1])
	}
}

func TestComputeDominatorsChain(t *testing.T) {
	cfg := NewCFG()
	cfg.Entry = 1
	cfg.AddNode(&CFGNode{ID: 1, Label: "entry"})
	cfg.AddNode(&CFGNode{ID: 2, Label: "b"})
	cfg.AddNode(&CFGNode{ID: 3, Label: "c"})
	cfg.AddEdge(1, 2)
	cfg.AddEdge(2, 3)
	dom := ComputeDominators(cfg)
	if dom.IDom[2] != 1 {
		t.Fatalf("expected idom[2]=1, got %d", dom.IDom[2])
	}
	if dom.IDom[3] != 2 {
		t.Fatalf("expected idom[3]=2, got %d", dom.IDom[3])
	}
}

func TestComputeDominatorsDiamond(t *testing.T) {
	cfg := NewCFG()
	cfg.Entry = 1
	for i := 1; i <= 4; i++ {
		cfg.AddNode(&CFGNode{ID: i, Label: fmt.Sprintf("b%d", i)})
	}
	cfg.AddEdge(1, 2)
	cfg.AddEdge(1, 3)
	cfg.AddEdge(2, 4)
	cfg.AddEdge(3, 4)
	dom := ComputeDominators(cfg)
	if dom.IDom[2] != 1 {
		t.Fatalf("expected idom[2]=1")
	}
	if dom.IDom[3] != 1 {
		t.Fatalf("expected idom[3]=1")
	}
	if dom.IDom[4] != 1 {
		t.Fatalf("expected idom[4]=1")
	}
}

func TestDominates(t *testing.T) {
	dom := &DominatorTree{IDom: map[int]int{1: 1, 2: 1, 3: 2}}
	if !dom.Dominates(1, 2) {
		t.Error("1 should dominate 2")
	}
	if !dom.Dominates(2, 3) {
		t.Error("2 should dominate 3")
	}
	if !dom.Dominates(3, 3) {
		t.Error("3 should dominate itself")
	}
	if dom.Dominates(3, 1) {
		t.Error("3 should not dominate 1")
	}
}

func TestFindLoopsEmpty(t *testing.T) {
	loops := FindLoops(NewCFG())
	if loops != nil && len(loops) != 0 {
		t.Fatalf("expected no loops")
	}
}

func TestFindLoopsBackEdge(t *testing.T) {
	cfg := NewCFG()
	cfg.Entry = 1
	cfg.AddNode(&CFGNode{ID: 1, Label: "header"})
	cfg.AddNode(&CFGNode{ID: 2, Label: "body"})
	cfg.AddEdge(1, 2)
	cfg.AddEdge(2, 1)
	loops := FindLoops(cfg)
	if len(loops) == 0 {
		t.Fatal("expected at least 1 loop")
	}
}

func TestLoopHierarchy(t *testing.T) {
	loops := []*Loop{
		{Header: 1, Members: map[int]bool{1: true, 2: true}},
		{Header: 2, Members: map[int]bool{2: true, 3: true}},
	}
	parent := LoopHierarchy(loops)
	if parent[2] != 1 {
		t.Fatalf("expected parent 2=1, got %d", parent[2])
	}
}

func TestNewMetadata(t *testing.T) {
	m := NewMetadata()
	if m.DebugInfo == nil || m.ProfileData == nil {
		t.Fatal("expected initialized maps")
	}
}

func TestPromoteType(t *testing.T) {
	if PromoteType("int32") != "int64" {
		t.Error("expected int64")
	}
	if PromoteType("unknown") != "unknown" {
		t.Error("expected unknown")
	}
}

func TestShapePropagatorAdd(t *testing.T) {
	s := NewShapePropagator()
	out := s.Propagate("add", []Shape{{2, 3}, {2, 3}})
	if len(out) != 2 || out[0] != 2 || out[1] != 3 {
		t.Fatalf("expected [2,3], got %v", out)
	}
}

func TestShapePropagatorMatMul(t *testing.T) {
	s := NewShapePropagator()
	out := s.Propagate("matmul", []Shape{{2, 3}, {3, 4}})
	if len(out) != 2 || out[0] != 2 || out[1] != 4 {
		t.Fatalf("expected [2,4], got %v", out)
	}
}

func TestMetadataString(t *testing.T) {
	m := NewMetadata()
	m.DebugInfo["loc"] = "main.go"
	s := m.String()
	if s == "" {
		t.Fatal("expected non-empty string")
	}
}
