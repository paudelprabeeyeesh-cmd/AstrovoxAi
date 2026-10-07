package ir

import "testing"

func TestNewCFG(t *testing.T) {
	cfg := NewCFG()
	if cfg.Nodes == nil {
		t.Fatal("expected nodes map")
	}
}

func TestAddNode(t *testing.T) {
	cfg := NewCFG()
	n := &CFGNode{ID: 1, Label: "entry"}
	cfg.AddNode(n)
	if cfg.Nodes[1] != n {
		t.Fatal("expected same node")
	}
}

func TestAddEdge(t *testing.T) {
	cfg := NewCFG()
	cfg.AddNode(&CFGNode{ID: 1, Label: "entry"})
	cfg.AddNode(&CFGNode{ID: 2, Label: "exit"})
	cfg.AddEdge(1, 2)
	if len(cfg.Nodes[1].Successors) != 1 || cfg.Nodes[1].Successors[0] != 2 {
		t.Fatal("expected edge")
	}
	if len(cfg.Nodes[2].Predecessors) != 1 || cfg.Nodes[2].Predecessors[0] != 1 {
		t.Fatal("expected predecessor")
	}
}

func TestAddEdgeNilNodes(t *testing.T) {
	cfg := NewCFG()
	cfg.AddEdge(1, 2)
	if len(cfg.Nodes) != 0 {
		t.Fatalf("expected no nodes")
	}
}

func TestAddEdgeSelf(t *testing.T) {
	cfg := NewCFG()
	cfg.AddNode(&CFGNode{ID: 1})
	cfg.AddEdge(1, 1)
	if len(cfg.Nodes[1].Successors) != 0 {
		t.Fatal("expected no self-edge")
	}
}

func TestCFGNodeStruct(t *testing.T) {
	n := CFGNode{ID: 1, Label: "entry"}
	if n.ID != 1 || n.Label != "entry" {
		t.Fatal("unexpected node")
	}
}

func TestCFGStruct(t *testing.T) {
	cfg := CFG{Nodes: make(map[int]*CFGNode)}
	if cfg.Nodes == nil {
		t.Fatal("expected nodes map")
	}
}

func TestCFGWithExit(t *testing.T) {
	cfg := NewCFG()
	cfg.Exit = 2
	if cfg.Exit != 2 {
		t.Fatal("expected exit 2")
	}
}

func TestMultipleEdges(t *testing.T) {
	cfg := NewCFG()
	cfg.AddNode(&CFGNode{ID: 1})
	cfg.AddNode(&CFGNode{ID: 2})
	cfg.AddNode(&CFGNode{ID: 3})
	cfg.AddEdge(1, 2)
	cfg.AddEdge(1, 3)
	if len(cfg.Nodes[1].Successors) != 2 {
		t.Fatalf("expected 2 successors")
	}
}
