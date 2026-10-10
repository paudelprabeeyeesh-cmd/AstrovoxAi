package gnn

import (
	"math"
	"testing"
)

func newTestGraph(t *testing.T, n, dim int) *Graph {
	t.Helper()
	g, err := NewGraph(n, dim)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < n; i++ {
		for d := 0; d < dim; d++ {
			g.Features[i][d] = float64(i + d)
		}
	}
	return g
}

func TestNewGraphInvalid(t *testing.T) {
	if _, err := NewGraph(0, 3); err != ErrEmptyGraph {
		t.Error("expected empty graph for 0 nodes")
	}
	if _, err := NewGraph(-1, 3); err != ErrEmptyGraph {
		t.Error("expected empty graph for negative nodes")
	}
	if _, err := NewGraph(3, 0); err != ErrInvalidDims {
		t.Error("expected dims error")
	}
}

func TestGraphAddEdge(t *testing.T) {
	g := newTestGraph(t, 4, 2)
	if err := g.AddEdge(0, 1, 1); err != nil {
		t.Fatal(err)
	}
	if err := g.AddEdge(1, 2, 1); err != nil {
		t.Fatal(err)
	}
	if g.NumEdges != 2 {
		t.Errorf("expected 2 edges, got %d", g.NumEdges)
	}
	if err := g.AddEdge(4, 0, 1); err != ErrInvalidIndex {
		t.Error("expected index error")
	}
	if err := g.AddEdge(0, -1, 1); err != ErrInvalidIndex {
		t.Error("expected index error")
	}
}

func TestGraphDensity(t *testing.T) {
	g := newTestGraph(t, 4, 1)
	if g.Density() != 0 {
		t.Error("empty graph density")
	}
	for i := 0; i < 4; i++ {
		if err := g.AddEdge(i, (i+1)%4, 1); err != nil {
			t.Fatal(err)
		}
	}
	want := 4.0 / 12.0
	if d := g.Density(); d < want-1e-9 || d > want+1e-9 {
		t.Errorf("got %f, want %f", d, want)
	}
}

func TestGraphDensitySingleNode(t *testing.T) {
	g := newTestGraph(t, 1, 1)
	if g.Density() != 0 {
		t.Error("single node density should be 0")
	}
}

func TestAdjacencyMatrix(t *testing.T) {
	g := newTestGraph(t, 3, 1)
	g.AddEdge(0, 1, 2)
	mat, err := g.AdjacencyMatrix()
	if err != nil {
		t.Fatal(err)
	}
	if mat[0][1] != 2 {
		t.Error("expected weight 2")
	}
	if mat[1][0] != 0 {
		t.Error("directed graph")
	}
}

func TestAddSelfLoopsAndNorm(t *testing.T) {
	g := newTestGraph(t, 3, 1)
	g.AddEdge(0, 1, 1)
	mat, err := g.AddSelfLoops()
	if err != nil {
		t.Fatal(err)
	}
	if mat[0][0] != 1 || mat[1][1] != 1 {
		t.Error("self loops")
	}
	norm, err := g.SymmetricNorm()
	if err != nil {
		t.Fatal(err)
	}
	// Degrees with self loops: d0 = 2 (self + edge to 1), d1 = 1, d2 = 1.
	// D^-1/2 (A+I) D^-1/2 row 0 = [1/d0, 1/sqrt(d0*d1), 0].
	if math.Abs(norm[0][0]-0.5) > 1e-9 {
		t.Errorf("norm[0][0] = %f, want 0.5", norm[0][0])
	}
	want := 1.0 / math.Sqrt(2.0)
	if math.Abs(norm[0][1]-want) > 1e-9 {
		t.Errorf("norm[0][1] = %f, want %f", norm[0][1], want)
	}
	if norm[0][2] != 0 {
		t.Error("expected zero for absent edge")
	}
	// Nodes without edges keep only the self-loop weight 1.
	if math.Abs(norm[2][2]-1.0) > 1e-9 {
		t.Errorf("norm[2][2] = %f, want 1", norm[2][2])
	}
}

func TestMessagePassAggregations(t *testing.T) {
	g := newTestGraph(t, 3, 1)
	g.AddEdge(0, 1, 1)
	g.AddEdge(0, 2, 1)
	W := [][]float64{{1}}
	for _, agg := range []string{"sum", "mean", "max"} {
		out, err := MessagePass(g, W, agg)
		if err != nil {
			t.Fatalf("%s: %v", agg, err)
		}
		if len(out) != 3 {
			t.Fatalf("%s: expected 3 nodes", agg)
		}
	}
}

func TestMessagePassInvalid(t *testing.T) {
	g := newTestGraph(t, 2, 3)
	if _, err := MessagePass(g, [][]float64{{1}}, "mean"); err != ErrInvalidDims {
		t.Error("expected dims error")
	}
	// An empty graph must be rejected.
	empty := &Graph{Features: [][]float64{}}
	if _, err := MessagePass(empty, [][]float64{{1}}, "mean"); err != ErrEmptyGraph {
		t.Error("expected empty graph error")
	}
}

func TestGCNLayer(t *testing.T) {
	g := newTestGraph(t, 4, 2)
	g.AddEdge(0, 1, 1)
	g.AddEdge(1, 2, 1)
	g.AddEdge(2, 3, 1)
	l, err := NewGCNLayer(2, 3, nil)
	if err != nil {
		t.Fatal(err)
	}
	out, err := l.Forward(g)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 4 || len(out[0]) != 3 {
		t.Errorf("shape: %dx%d", len(out), len(out[0]))
	}
}

func TestGCNLayerInvalid(t *testing.T) {
	if _, err := NewGCNLayer(0, 3, nil); err != ErrInvalidDims {
		t.Error("expected dims error")
	}
	l, _ := NewGCNLayer(2, 2, nil)
	g := newTestGraph(t, 3, 5) // wrong feature dim
	if _, err := l.Forward(g); err != ErrInvalidDims {
		t.Error("expected dims error on forward")
	}
}

func TestGCNLayerDefaultActivation(t *testing.T) {
	g := newTestGraph(t, 3, 2)
	g.AddEdge(0, 1, 1)
	l, _ := NewGCNLayer(2, 2, nil)
	if l.activation == nil {
		t.Fatal("expected default activation")
	}
	out, err := l.Forward(g)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 3 {
		t.Error("output shape")
	}
}

func TestGATHeadAttentionSums(t *testing.T) {
	g := newTestGraph(t, 3, 2)
	g.AddEdge(0, 1, 1)
	g.AddEdge(2, 1, 1)
	h, err := NewGATHead(2, 2)
	if err != nil {
		t.Fatal(err)
	}
	scores, err := h.AttentionScores(g)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 3; i++ {
		sum := 0.0
		for _, s := range scores[i] {
			sum += s
		}
		if sum < 0.999 || sum > 1.001 {
			t.Errorf("node %d attention sum = %f", i, sum)
		}
	}
}

func TestGATHeadForward(t *testing.T) {
	g := newTestGraph(t, 3, 2)
	g.AddEdge(0, 1, 1)
	g.AddEdge(1, 2, 1)
	h, _ := NewGATHead(2, 3)
	out, err := h.Forward(g)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 3 || len(out[0]) != 3 {
		t.Errorf("shape %dx%d", len(out), len(out[0]))
	}
}

func TestGATHeadInvalid(t *testing.T) {
	if _, err := NewGATHead(0, 3); err != ErrInvalidDims {
		t.Error("expected dims error")
	}
	h, _ := NewGATHead(2, 2)
	g := newTestGraph(t, 3, 9)
	if _, err := h.Forward(g); err != ErrInvalidDims {
		t.Error("expected dims error")
	}
}

func TestGATLayerMultiHead(t *testing.T) {
	g := newTestGraph(t, 4, 2)
	g.AddEdge(0, 1, 1)
	g.AddEdge(1, 2, 1)
	g.AddEdge(2, 3, 1)

	concat, err := NewGATLayer(2, 3, 2, true)
	if err != nil {
		t.Fatal(err)
	}
	out, err := concat.Forward(g)
	if err != nil {
		t.Fatal(err)
	}
	if len(out[0]) != 6 {
		t.Errorf("concat should double the dim, got %d", len(out[0]))
	}

	avg, _ := NewGATLayer(2, 3, 2, false)
	out2, err := avg.Forward(g)
	if err != nil {
		t.Fatal(err)
	}
	if len(out2[0]) != 3 {
		t.Errorf("average should keep the dim, got %d", len(out2[0]))
	}
}

func TestGATLayerInvalid(t *testing.T) {
	if _, err := NewGATLayer(2, 3, 0, true); err != ErrInvalidDims {
		t.Error("expected heads error")
	}
}

func TestLeakyReLU(t *testing.T) {
	if leakyReLU(5, 0.2) != 5 {
		t.Error("positive passthrough")
	}
	if leakyReLU(-5, 0.2) != -1 {
		t.Errorf("expected -1, got %f", leakyReLU(-5, 0.2))
	}
}
