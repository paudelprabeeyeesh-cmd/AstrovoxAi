package graph

import (
	"sort"
	"sync"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Graph is a directed acyclic dataflow graph of operators.
type Graph struct {
	mu      sync.RWMutex
	nodes   []*Node
	edges   []*Edge
	nextID  int
	name    string
	outputs map[int]bool
}

// New creates an empty graph.
func New(name string) *Graph {
	return &Graph{name: name}
}

// Name returns the graph name.
func (g *Graph) Name() string { return g.name }

// AddNode appends an operator node and returns its ID.
func (g *Graph) AddNode(op Op, attrs map[string]any) (int, error) {
	if op == nil {
		return 0, errors.New(errors.CodeInvalidArgument, "nil operator")
	}
	g.mu.Lock()
	defer g.mu.Unlock()
	id := g.nextID
	g.nextID++
	g.nodes = append(g.nodes, &Node{ID: id, Op: op, Attrs: attrs})
	return id, nil
}

// AddEdge connects output port fromPort of node from to
// input port toPort of node to. Edges that would create
// a cycle are rejected and rolled back.
func (g *Graph) AddEdge(from, to, fromPort, toPort int) (int, error) {
	g.mu.Lock()
	defer g.mu.Unlock()
	spec := EdgeSpec{From: from, To: to, FromPort: fromPort, ToPort: toPort}
	if err := spec.Validate(g.nextID, nil, nil); err != nil {
		return 0, err
	}
	id := len(g.edges)
	edge := &Edge{ID: id, From: from, To: to, FromPort: fromPort, ToPort: toPort}
	g.edges = append(g.edges, edge)
	g.nodes[from].Outputs = append(g.nodes[from].Outputs, id)
	g.nodes[to].Inputs = append(g.nodes[to].Inputs, id)
	// A cycle exists iff `to` can already reach `from`.
	if g.reachesLocked(to, from) {
		// Roll back the edge: it created a cycle.
		g.edges = g.edges[:len(g.edges)-1]
		g.nodes[from].Outputs = g.nodes[from].Outputs[:len(g.nodes[from].Outputs)-1]
		g.nodes[to].Inputs = g.nodes[to].Inputs[:len(g.nodes[to].Inputs)-1]
		return 0, errors.New(errors.CodeCycleDetected, "edge creates a cycle").
			WithField("from", from).WithField("to", to)
	}
	return id, nil
}

// reachesLocked reports whether target is reachable
// from src via forward edges. The caller must hold
// the lock.
func (g *Graph) reachesLocked(src, target int) bool {
	if src == target {
		return true
	}
	visited := make([]bool, len(g.nodes))
	stack := make([]int, 0, 16)
	stack = append(stack, src)
	for len(stack) > 0 {
		n := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if n == target {
			return true
		}
		if visited[n] {
			continue
		}
		visited[n] = true
		for _, eid := range g.nodes[n].Outputs {
			e := g.edge(eid)
			if e != nil && !visited[e.To] {
				stack = append(stack, e.To)
			}
		}
	}
	return false
}

// Connect adds edges for each (from, to) pair on port 0.
func (g *Graph) Connect(pairs [][2]int) error {
	for _, p := range pairs {
		if _, err := g.AddEdge(p[0], p[1], 0, 0); err != nil {
			return err
		}
	}
	return nil
}

// Nodes returns a copy of the live node list.
func (g *Graph) Nodes() []*Node {
	g.mu.RLock()
	defer g.mu.RUnlock()
	out := make([]*Node, 0, len(g.nodes))
	for _, n := range g.nodes {
		if n != nil && !n.removed {
			out = append(out, n)
		}
	}
	return out
}

// Edges returns a copy of the live edge list.
func (g *Graph) Edges() []*Edge {
	g.mu.RLock()
	defer g.mu.RUnlock()
	out := make([]*Edge, 0, len(g.edges))
	for _, e := range g.edges {
		if e != nil && !e.removed {
			out = append(out, e)
		}
	}
	return out
}

// edge returns the edge with the given ID,
// or nil when out of range or tombstoned.
// The caller must hold the lock.
func (g *Graph) edge(eid int) *Edge {
	if eid < 0 || eid >= len(g.edges) {
		return nil
	}
	e := g.edges[eid]
	if e == nil || e.removed {
		return nil
	}
	return e
}

// NodeCount returns the number of live nodes.
func (g *Graph) NodeCount() int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	count := 0
	for _, n := range g.nodes {
		if n != nil && !n.removed {
			count++
		}
	}
	return count
}

// EdgeCount returns the number of live edges.
func (g *Graph) EdgeCount() int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	count := 0
	for _, e := range g.edges {
		if e != nil && !e.removed {
			count++
		}
	}
	return count
}

// Node returns the node with the given ID.
func (g *Graph) Node(id int) (*Node, error) {
	g.mu.RLock()
	defer g.mu.RUnlock()
	if id < 0 || id >= len(g.nodes) {
		return nil, errors.New(errors.CodeNotFound, "node not found").
			WithField("id", id)
	}
	return g.nodes[id], nil
}

// Adjacency returns the forward adjacency list.
func (g *Graph) Adjacency() map[int][]int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	adj := make(map[int][]int, len(g.nodes))
	for _, e := range g.edges {
		adj[e.From] = append(adj[e.From], e.To)
	}
	return adj
}

// MarkOutput designates a node as a graph
// output. Designated outputs anchor dead-code
// elimination and determine executor sinks.
func (g *Graph) MarkOutput(id int) error {
	g.mu.Lock()
	defer g.mu.Unlock()
	if id < 0 || id >= len(g.nodes) {
		return errors.New(errors.CodeNotFound, "node not found").
			WithField("id", id)
	}
	if g.outputs == nil {
		g.outputs = map[int]bool{}
	}
	g.outputs[id] = true
	return nil
}

// Outputs returns the designated output node IDs.
func (g *Graph) Outputs() []int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	out := make([]int, 0, len(g.outputs))
	for id := range g.outputs {
		out = append(out, id)
	}
	sort.Ints(out)
	return out
}

// TopologicalSort returns node IDs in dependency order
// (Kahn's algorithm). Deterministic: ties broken by node ID.
func (g *Graph) TopologicalSort() ([]int, error) {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.topologicalSortLocked()
}

// topologicalSortLocked runs Kahn's algorithm;
// the caller must hold the lock. Tombstoned
// nodes and edges are skipped.
func (g *Graph) topologicalSortLocked() ([]int, error) {
	live := 0
	for _, n := range g.nodes {
		if n != nil && !n.removed {
			live++
		}
	}
	indeg := make([]int, len(g.nodes))
	adj := make(map[int][]int, len(g.nodes))
	for _, e := range g.edges {
		if e == nil || e.removed {
			continue
		}
		if g.nodes[e.From] == nil || g.nodes[e.From].removed {
			continue
		}
		if g.nodes[e.To] == nil || g.nodes[e.To].removed {
			continue
		}
		adj[e.From] = append(adj[e.From], e.To)
		indeg[e.To]++
	}
	var ready []int
	for i, n := range g.nodes {
		if n == nil || n.removed {
			continue
		}
		if indeg[i] == 0 {
			ready = append(ready, i)
		}
	}
	sort.Ints(ready)
	out := make([]int, 0, live)
	for len(ready) > 0 {
		n := ready[0]
		ready = ready[1:]
		out = append(out, n)
		next := append([]int(nil), adj[n]...)
		sort.Ints(next)
		for _, m := range next {
			indeg[m]--
			if indeg[m] == 0 {
				ready = append(ready, m)
				sort.Ints(ready)
			}
		}
	}
	if len(out) != live {
		return nil, errors.New(errors.CodeCycleDetected, "graph contains a cycle").
			WithField("sorted", len(out)).WithField("nodes", live)
	}
	return out, nil
}

// HasCycle reports whether the graph contains a cycle.
func (g *Graph) HasCycle() bool {
	_, err := g.TopologicalSort()
	return err != nil
}

// Validate checks structural and semantic invariants:
// acyclicity, port arity, and shape inference.
func (g *Graph) Validate() error {
	if _, err := g.TopologicalSort(); err != nil {
		return err
	}
	g.mu.RLock()
	defer g.mu.RUnlock()
	for _, n := range g.nodes {
		if n == nil || n.removed {
			continue
		}
		seen := map[int]bool{}
		for _, eid := range n.Inputs {
			e := g.edge(eid)
			if e == nil || e.To != n.ID {
				return errors.New(errors.CodeInternal, "edge endpoint mismatch").
					WithField("edge", eid).WithField("node", n.ID)
			}
			if seen[e.ToPort] {
				return errors.New(errors.CodeInvalidArgument, "duplicate input port").
					WithField("node", n.ID).WithField("port", e.ToPort)
			}
			seen[e.ToPort] = true
		}
	}
	order, err := g.TopologicalSort()
	if err != nil {
		return err
	}
	for _, id := range order {
		n := g.nodes[id]
		if n == nil || n.removed {
			continue
		}
		inputs := make([]tensor.Shape, 0, len(n.Inputs))
		for _, eid := range n.Inputs {
			e := g.edge(eid)
			if e == nil {
				continue
			}
			src := g.nodes[e.From]
			if src == nil || src.removed {
				continue
			}
			if e.FromPort >= len(src.outShapes) {
				return errors.New(errors.CodeInvalidArgument, "source port exceeds outputs").
					WithField("node", src.ID).WithField("op", src.Op.Name())
			}
			inputs = append(inputs, src.outShapes[e.FromPort])
		}
		shapes, err := n.Op.InferShape(inputs)
		if err != nil {
			return errors.Wrap(err, errors.CodeInvalidArgument, "shape inference failed").
				WithField("node", n.ID).WithField("op", n.Op.Name())
		}
		n.outShapes = shapes
	}
	return nil
}
