// Package gnn implements graph neural networks: graph structures,
// message passing, and GCN/GAT layers.
package gnn

import (
	"errors"
	"math"
)

// GNN errors.
var (
	ErrEmptyGraph   = errors.New("graph has no nodes")
	ErrInvalidDims  = errors.New("feature or weight dimensions mismatch")
	ErrInvalidIndex = errors.New("node index out of range")
	ErrNilAdjacency = errors.New("adjacency matrix is nil")
)

// Graph is a directed graph with node features and edge structure.
type Graph struct {
	NumNodes int
	NumEdges int
	Features [][]float64 // [numNodes][featDim]
	Edges    []Edge
	Adj      [][]int // adjacency lists (out edges)
}

// Edge is a directed edge with an optional weight.
type Edge struct {
	Src    int
	Dst    int
	Weight float64
}

// NewGraph creates a graph with the given node count and feature dim.
func NewGraph(numNodes, featDim int) (*Graph, error) {
	if numNodes <= 0 {
		return nil, ErrEmptyGraph
	}
	if featDim <= 0 {
		return nil, ErrInvalidDims
	}
	g := &Graph{
		NumNodes: numNodes,
		Features: make([][]float64, numNodes),
		Adj:      make([][]int, numNodes),
	}
	for i := range g.Features {
		g.Features[i] = make([]float64, featDim)
	}
	return g, nil
}

// AddEdge adds a directed edge.
func (g *Graph) AddEdge(src, dst int, weight float64) error {
	if src < 0 || src >= g.NumNodes || dst < 0 || dst >= g.NumNodes {
		return ErrInvalidIndex
	}
	if weight == 0 {
		weight = 1.0
	}
	g.Edges = append(g.Edges, Edge{Src: src, Dst: dst, Weight: weight})
	g.NumEdges++
	g.Adj[src] = append(g.Adj[src], g.NumEdges-1)
	return nil
}

// Density returns the edge density.
func (g *Graph) Density() float64 {
	if g.NumNodes <= 1 {
		return 0
	}
	maxEdges := float64(g.NumNodes * (g.NumNodes - 1))
	return float64(g.NumEdges) / maxEdges
}

// AdjacencyMatrix builds a dense weighted adjacency matrix.
func (g *Graph) AdjacencyMatrix() ([][]float64, error) {
	if g == nil {
		return nil, ErrNilAdjacency
	}
	mat := make([][]float64, g.NumNodes)
	for i := range mat {
		mat[i] = make([]float64, g.NumNodes)
	}
	for _, e := range g.Edges {
		mat[e.Src][e.Dst] = e.Weight
	}
	return mat, nil
}

// AddSelfLoops returns an adjacency matrix augmented with self-loops.
func (g *Graph) AddSelfLoops() ([][]float64, error) {
	mat, err := g.AdjacencyMatrix()
	if err != nil {
		return nil, err
	}
	for i := range mat {
		mat[i][i] += 1.0
	}
	return mat, nil
}

// SymmetricNorm returns D^-1/2 (A + I) D^-1/2, the GCN normalisation.
func (g *Graph) SymmetricNorm() ([][]float64, error) {
	mat, err := g.AddSelfLoops()
	if err != nil {
		return nil, err
	}
	degree := make([]float64, g.NumNodes)
	for i := range mat {
		for j := range mat[i] {
			degree[i] += mat[i][j]
		}
	}
	for i := range mat {
		di := 1.0
		if degree[i] > 0 {
			di = 1.0 / math.Sqrt(degree[i])
		}
		for j := range mat[i] {
			dj := 1.0
			if degree[j] > 0 {
				dj = 1.0 / math.Sqrt(degree[j])
			}
			mat[i][j] *= di * dj
		}
	}
	return mat, nil
}

// MessagePass performs one round of neighbourhood aggregation:
//
//	h_i' = aggregate over j in N(i) of (W h_j)
//
// where W ([inDim][outDim]) is applied to every node feature first.
func MessagePass(g *Graph, W [][]float64, aggregate string) ([][]float64, error) {
	if g == nil || len(g.Features) == 0 {
		return nil, ErrEmptyGraph
	}
	if len(W) == 0 || len(W[0]) == 0 {
		return nil, ErrInvalidDims
	}
	featDim := len(g.Features[0])
	outDim := len(W[0])
	if featDim != len(W) {
		return nil, ErrInvalidDims
	}

	// Transform features.
	transformed := make([][]float64, g.NumNodes)
	for i := range transformed {
		transformed[i] = make([]float64, outDim)
		for a := 0; a < outDim; a++ {
			sum := 0.0
			for k := 0; k < featDim; k++ {
				sum += g.Features[i][k] * W[k][a]
			}
			transformed[i][a] = sum
		}
	}

	// Aggregate neighbour messages (including self).
	out := make([][]float64, g.NumNodes)
	for i := range out {
		out[i] = make([]float64, outDim)
		neighbours := g.Adj[i]
		// Precompute the weighted neighbour contributions once per node.
		contribs := make([][]float64, len(neighbours))
		for k, eIdx := range neighbours {
			e := g.Edges[eIdx]
			contribs[k] = make([]float64, outDim)
			for a := 0; a < outDim; a++ {
				contribs[k][a] = e.Weight * transformed[e.Dst][a]
			}
		}
		for a := 0; a < outDim; a++ {
			switch aggregate {
			case "sum":
				acc := transformed[i][a]
				for _, c := range contribs {
					acc += c[a]
				}
				out[i][a] = acc
			case "max":
				m := transformed[i][a]
				for _, c := range contribs {
					if c[a] > m {
						m = c[a]
					}
				}
				out[i][a] = m
			default: // mean
				acc := transformed[i][a]
				count := 1
				for _, c := range contribs {
					acc += c[a]
					count++
				}
				out[i][a] = acc / float64(count)
			}
		}
	}
	return out, nil
}

// GCNLayer is a graph convolution layer: H' = activation(A_hat H W).
type GCNLayer struct {
	W          [][]float64
	inDim      int
	outDim     int
	activation func(float64) float64
	dropout    float64
}

// NewGCNLayer creates a GCN layer.
func NewGCNLayer(inDim, outDim int, activation func(float64) float64) (*GCNLayer, error) {
	if inDim <= 0 || outDim <= 0 {
		return nil, ErrInvalidDims
	}
	w := make([][]float64, inDim)
	for i := range w {
		w[i] = make([]float64, outDim)
	}
	if activation == nil {
		activation = math.Tanh
	}
	return &GCNLayer{W: w, inDim: inDim, outDim: outDim, activation: activation}, nil
}

// Forward applies the GCN layer to a graph.
func (l *GCNLayer) Forward(g *Graph) ([][]float64, error) {
	if len(g.Features) == 0 {
		return nil, ErrEmptyGraph
	}
	if len(g.Features[0]) != l.inDim {
		return nil, ErrInvalidDims
	}
	norm, err := g.SymmetricNorm()
	if err != nil {
		return nil, err
	}

	// H' = activation(A_hat * (H W))
	hw, err := MessagePass(g, l.W, "mean")
	if err != nil {
		return nil, err
	}
	out := make([][]float64, g.NumNodes)
	for i := range out {
		out[i] = make([]float64, l.outDim)
		for a := 0; a < l.outDim; a++ {
			sum := 0.0
			for j := 0; j < g.NumNodes; j++ {
				if norm[i][j] != 0 {
					sum += norm[i][j] * hw[j][a]
				}
			}
			out[i][a] = l.activation(sum)
		}
	}
	return out, nil
}

// GATHead is one attention head of a graph attention layer.
type GATHead struct {
	W      [][]float64 // [inDim][outDim]
	a      []float64   // attention parameters [2*outDim]
	inDim  int
	outDim int
}

// NewGATHead creates a GAT head.
func NewGATHead(inDim, outDim int) (*GATHead, error) {
	if inDim <= 0 || outDim <= 0 {
		return nil, ErrInvalidDims
	}
	w := make([][]float64, inDim)
	for i := range w {
		w[i] = make([]float64, outDim)
	}
	return &GATHead{W: w, a: make([]float64, 2*outDim), inDim: inDim, outDim: outDim}, nil
}

// AttentionScores returns normalised attention coefficients for each node's
// in-edges plus the self-loop.
func (h *GATHead) AttentionScores(g *Graph) ([][]float64, error) {
	if len(g.Features) == 0 {
		return nil, ErrEmptyGraph
	}
	if len(g.Features[0]) != h.inDim {
		return nil, ErrInvalidDims
	}

	// Transform features.
	transformed := make([][]float64, g.NumNodes)
	for i := range transformed {
		transformed[i] = make([]float64, h.outDim)
		for a := 0; a < h.outDim; a++ {
			sum := 0.0
			for k := 0; k < h.inDim; k++ {
				sum += g.Features[i][k] * h.W[k][a]
			}
			transformed[i][a] = sum
		}
	}

	// LeakyReLU attention logits followed by softmax over neighbours.
	scores := make([][]float64, g.NumNodes)
	for i := 0; i < g.NumNodes; i++ {
		// Neighbour set includes the node itself.
		nbs := []int{i}
		for _, e := range g.Edges {
			if e.Dst == i {
				nbs = append(nbs, e.Src)
			}
		}
		logits := make([]float64, len(nbs))
		for j, jIdx := range nbs {
			dot := 0.0
			for a := 0; a < h.outDim; a++ {
				dot += h.a[a]*transformed[i][a] + h.a[h.outDim+a]*transformed[jIdx][a]
			}
			logits[j] = leakyReLU(dot, 0.2)
		}
		scores[i] = softmax(logits)
	}
	return scores, nil
}

// Forward applies one GAT head.
func (h *GATHead) Forward(g *Graph) ([][]float64, error) {
	scores, err := h.AttentionScores(g)
	if err != nil {
		return nil, err
	}
	transformed := make([][]float64, g.NumNodes)
	for i := range transformed {
		transformed[i] = make([]float64, h.outDim)
		for a := 0; a < h.outDim; a++ {
			sum := 0.0
			for k := 0; k < h.inDim; k++ {
				sum += g.Features[i][k] * h.W[k][a]
			}
			transformed[i][a] = sum
		}
	}

	out := make([][]float64, g.NumNodes)
	for i := range out {
		out[i] = make([]float64, h.outDim)
		nbs := []int{i}
		for _, e := range g.Edges {
			if e.Dst == i {
				nbs = append(nbs, e.Src)
			}
		}
		for j, jIdx := range nbs {
			coef := scores[i][j]
			for a := 0; a < h.outDim; a++ {
				out[i][a] += coef * transformed[jIdx][a]
			}
		}
	}
	return out, nil
}

// GATLayer aggregates multiple attention heads.
type GATLayer struct {
	Heads  []*GATHead
	Concat bool
}

// NewGATLayer creates a multi-head GAT layer.
func NewGATLayer(inDim, outDim, heads int, concat bool) (*GATLayer, error) {
	if heads <= 0 {
		return nil, ErrInvalidDims
	}
	hs := make([]*GATHead, heads)
	for i := range hs {
		h, err := NewGATHead(inDim, outDim)
		if err != nil {
			return nil, err
		}
		hs[i] = h
	}
	return &GATLayer{Heads: hs, Concat: concat}, nil
}

// Forward applies all heads and concatenates or averages them.
func (l *GATLayer) Forward(g *Graph) ([][]float64, error) {
	outs := make([][][]float64, len(l.Heads))
	for i, h := range l.Heads {
		o, err := h.Forward(g)
		if err != nil {
			return nil, err
		}
		outs[i] = o
	}

	n := len(outs[0])
	d := len(outs[0][0])

	if !l.Concat {
		// Average heads.
		out := make([][]float64, n)
		for i := range out {
			out[i] = make([]float64, d)
			for a := 0; a < d; a++ {
				sum := 0.0
				for _, h := range outs {
					sum += h[i][a]
				}
				out[i][a] = sum / float64(len(outs))
			}
		}
		return out, nil
	}

	// Concatenate heads.
	out := make([][]float64, n)
	for i := range out {
		out[i] = make([]float64, d*len(outs))
		for hIdx, h := range outs {
			for a := 0; a < d; a++ {
				out[i][hIdx*d+a] = h[i][a]
			}
		}
	}
	return out, nil
}

func leakyReLU(x, alpha float64) float64 {
	if x > 0 {
		return x
	}
	return alpha * x
}

func softmax(v []float64) []float64 {
	if len(v) == 0 {
		return nil
	}
	maxV := v[0]
	for _, x := range v {
		if x > maxV {
			maxV = x
		}
	}
	out := make([]float64, len(v))
	sum := 0.0
	for i, x := range v {
		out[i] = math.Exp(x - maxV)
		sum += out[i]
	}
	if sum > 0 {
		for i := range out {
			out[i] /= sum
		}
	}
	return out
}
