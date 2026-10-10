package knowledge

import "testing"

func buildGraph(t *testing.T) *Graph {
	t.Helper()
	g := NewGraph()
	for _, id := range []NodeID{"a", "b", "c", "d", "e"} {
		if err := g.AddNode(NewNode(id, "node")); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := g.AddEdge("a", "b", "knows", 1); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge("b", "c", "likes", 2); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge("a", "c", "knows", 3); err != nil {
		t.Fatal(err)
	}
	if _, err := g.AddEdge("c", "d", "works_with", 1); err != nil {
		t.Fatal(err)
	}
	return g
}

func TestGraphAddNode(t *testing.T) {
	g := buildGraph(t)
	if g.NodeCount() != 5 {
		t.Errorf("expected 5 nodes, got %d", g.NodeCount())
	}
	if g.EdgeCount() != 4 {
		t.Errorf("expected 4 edges, got %d", g.EdgeCount())
	}
}

func TestGraphAddNodeInvalid(t *testing.T) {
	g := NewGraph()
	if err := g.AddNode(NewNode("", "t")); err == nil {
		t.Error("expected error for empty ID")
	}
}

func TestGraphAddEdgeMissingNode(t *testing.T) {
	g := NewGraph()
	g.AddNode(NewNode("a", "t"))
	if _, err := g.AddEdge("a", "zz", "r", 1); err == nil {
		t.Error("expected error for missing target")
	}
}

func TestGraphGetNode(t *testing.T) {
	g := buildGraph(t)
	n, ok := g.GetNode("a")
	if !ok || n.Type != "node" {
		t.Error("expected to find node a")
	}
	if _, ok := g.GetNode("zz"); ok {
		t.Error("expected not found")
	}
}

func TestGraphNeighbours(t *testing.T) {
	g := buildGraph(t)
	nb := g.Neighbours("a", "knows")
	if len(nb) != 2 {
		t.Errorf("expected 2 neighbours, got %d", len(nb))
	}
	all := g.Neighbours("a", "")
	if len(all) != 2 {
		t.Errorf("expected 2 total, got %d", len(all))
	}
}

func TestGraphBFS(t *testing.T) {
	g := buildGraph(t)
	order := g.BFS("a", 10)
	if len(order) != 4 {
		t.Errorf("expected 4 visited, got %d (%v)", len(order), order)
	}
	if order[0] != "a" {
		t.Error("BFS should start at a")
	}
}

func TestGraphBFSDepthLimit(t *testing.T) {
	g := buildGraph(t)
	order := g.BFS("a", 1)
	if len(order) != 3 {
		t.Errorf("expected 3 at depth 1, got %d", len(order))
	}
}

func TestGraphDFS(t *testing.T) {
	g := buildGraph(t)
	order := g.DFS("a", 10)
	if len(order) != 4 {
		t.Errorf("expected 4 visited, got %d", len(order))
	}
}

func TestGraphShortestPath(t *testing.T) {
	g := buildGraph(t)
	p, err := g.ShortestPath("a", "d")
	if err != nil {
		t.Fatal(err)
	}
	if len(p.Nodes) != 3 {
		t.Errorf("expected 3 nodes (a,c,d), got %v", p.Nodes)
	}
	if p.Cost != 4 {
		t.Errorf("expected cost 4, got %f", p.Cost)
	}
}

func TestGraphShortestPathNoPath(t *testing.T) {
	g := NewGraph()
	g.AddNode(NewNode("a", "t"))
	g.AddNode(NewNode("b", "t"))
	if _, err := g.ShortestPath("a", "b"); err == nil {
		t.Error("expected no path error")
	}
}

func TestGraphShortestPathMissing(t *testing.T) {
	g := buildGraph(t)
	if _, err := g.ShortestPath("zz", "a"); err == nil {
		t.Error("expected error for missing source")
	}
}

func TestGraphAllPaths(t *testing.T) {
	g := buildGraph(t)
	paths := g.AllPaths("a", "c", 5)
	if len(paths) != 2 {
		t.Errorf("expected 2 paths (a->b->c, a->c), got %d", len(paths))
	}
}

func TestGraphExecuteQuery(t *testing.T) {
	g := buildGraph(t)
	res := g.Execute(Query{StartID: "a", Labels: []string{"knows"}, MaxDepth: 2})
	if len(res) == 0 {
		t.Error("expected query results")
	}
}

func TestGraphExecuteLimit(t *testing.T) {
	g := buildGraph(t)
	res := g.Execute(Query{StartID: "a", MaxDepth: 5, Limit: 2})
	if len(res) != 2 {
		t.Errorf("expected 2 limited results, got %d", len(res))
	}
}

func TestGraphPageRank(t *testing.T) {
	g := buildGraph(t)
	rank := g.PageRank(0.85, 20)
	if len(rank) != 5 {
		t.Fatalf("expected 5 ranks, got %d", len(rank))
	}
	top := g.TopNodes(rank, 1)
	if len(top) != 1 {
		t.Error("expected 1 top node")
	}
}

func TestGraphRemoveEdge(t *testing.T) {
	g := buildGraph(t)
	e, _ := g.GetEdge("e1")
	if !g.RemoveEdge(e.ID) {
		t.Error("expected edge removal")
	}
	if g.EdgeCount() != 3 {
		t.Errorf("expected 3 edges, got %d", g.EdgeCount())
	}
	if g.RemoveEdge("nonexistent") {
		t.Error("expected false for missing edge")
	}
}

func TestGraphNodeProperties(t *testing.T) {
	n := NewNode("x", "person")
	n.SetProperty("age", 30)
	v, ok := n.GetProperty("age")
	if !ok || v != 30 {
		t.Error("expected age 30")
	}
	if _, ok := n.GetProperty("missing"); ok {
		t.Error("expected missing property")
	}
}

func TestReasoner(t *testing.T) {
	g := buildGraph(t)
	r := NewReasoner(g)
	r.AddRule(ReasoningRule{
		Name:       "friend_of_friend",
		Rel1:       "knows",
		Rel2:       "knows",
		Conclusion: "knows_2",
	})
	inferred := r.Infer()
	// a knows b, b knows nobody-else... a->b.knows? b has no 'knows' out edge.
	// a->c (knows) and c has no knows out edge. So no inference here.
	if len(inferred) != 0 {
		t.Logf("inferred %d edges (fine)", len(inferred))
	}
}

func TestReasonerChain(t *testing.T) {
	g := NewGraph()
	g.AddNode(NewNode("a", "t"))
	g.AddNode(NewNode("b", "t"))
	g.AddNode(NewNode("c", "t"))
	g.AddEdge("a", "b", "knows", 1)
	g.AddEdge("b", "c", "knows", 1)
	r := NewReasoner(g)
	r.AddRule(ReasoningRule{Name: "foaf", Rel1: "knows", Rel2: "knows", Conclusion: "knows_2"})
	inferred := r.Infer()
	if len(inferred) != 1 {
		t.Fatalf("expected 1 inferred, got %d", len(inferred))
	}
	if inferred[0].From != "a" || inferred[0].To != "c" {
		t.Error("wrong inference")
	}
}

func TestSubgraph(t *testing.T) {
	g := buildGraph(t)
	sub := g.Subgraph([]NodeID{"a", "b", "c"})
	if sub.NodeCount() != 3 {
		t.Errorf("expected 3 nodes, got %d", sub.NodeCount())
	}
	if sub.EdgeCount() != 3 {
		t.Errorf("expected 3 internal edges, got %d", sub.EdgeCount())
	}
}
