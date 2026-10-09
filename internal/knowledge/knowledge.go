// Package knowledge provides a knowledge graph with nodes, edges,
// traversal, path finding, and simple reasoning.
package knowledge

import (
	"errors"
	"sort"
	"sync"
)

// NodeID identifies a graph node.
type NodeID string

// EdgeID identifies an edge.
type EdgeID string

// Node is an entity in the knowledge graph.
type Node struct {
	ID    NodeID
	Type  string
	Props map[string]interface{}
	mu    sync.RWMutex
}

// NewNode creates a node.
func NewNode(id NodeID, typ string) *Node {
	return &Node{ID: id, Type: typ, Props: make(map[string]interface{})}
}

// GetProperty returns a property value.
func (n *Node) GetProperty(key string) (interface{}, bool) {
	n.mu.RLock()
	defer n.mu.RUnlock()
	v, ok := n.Props[key]
	return v, ok
}

// SetProperty sets a property.
func (n *Node) SetProperty(key string, value interface{}) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.Props[key] = value
}

// Edge is a directed, labelled relation between two nodes.
type Edge struct {
	ID     EdgeID
	From   NodeID
	To     NodeID
	Label  string
	Weight float64
	Props  map[string]interface{}
}

// Graph is an in-memory knowledge graph.
type Graph struct {
	mu     sync.RWMutex
	nodes  map[NodeID]*Node
	edges  map[EdgeID]*Edge
	out    map[NodeID][]*Edge
	inEdges map[NodeID][]*Edge
	nextID int64
}

// NewGraph creates an empty graph.
func NewGraph() *Graph {
	return &Graph{
		nodes:  make(map[NodeID]*Node),
		edges:  make(map[EdgeID]*Edge),
		out:    make(map[NodeID][]*Edge),
		inEdges: make(map[NodeID][]*Edge),
	}
}

// AddNode adds a node, replacing an existing one with the same ID.
func (g *Graph) AddNode(n *Node) error {
	if n == nil || n.ID == "" {
		return errors.New("node must have an ID")
	}
	g.mu.Lock()
	defer g.mu.Unlock()
	g.nodes[n.ID] = n
	return nil
}

// AddEdge adds a directed edge, creating the ID automatically.
func (g *Graph) AddEdge(from, to NodeID, label string, weight float64) (*Edge, error) {
	g.mu.Lock()
	defer g.mu.Unlock()
	if _, ok := g.nodes[from]; !ok {
		return nil, errors.New("source node not found")
	}
	if _, ok := g.nodes[to]; !ok {
		return nil, errors.New("target node not found")
	}
	g.nextID++
	e := &Edge{
		ID:     EdgeID("e" + itoa64(g.nextID)),
		From:   from,
		To:     to,
		Label:  label,
		Weight: weight,
		Props:  make(map[string]interface{}),
	}
	g.edges[e.ID] = e
	g.out[from] = append(g.out[from], e)
	g.inEdges[to] = append(g.inEdges[to], e)
	return e, nil
}

// GetNode returns a node by ID.
func (g *Graph) GetNode(id NodeID) (*Node, bool) {
	g.mu.RLock()
	defer g.mu.RUnlock()
	n, ok := g.nodes[id]
	return n, ok
}

// GetEdge returns an edge by ID.
func (g *Graph) GetEdge(id EdgeID) (*Edge, bool) {
	g.mu.RLock()
	defer g.mu.RUnlock()
	e, ok := g.edges[id]
	return e, ok
}

// OutEdges returns the outgoing edges of a node.
func (g *Graph) OutEdges(id NodeID) []*Edge {
	g.mu.RLock()
	defer g.mu.RUnlock()
	out := make([]*Edge, len(g.out[id]))
	copy(out, g.out[id])
	return out
}

// InEdges returns the incoming edges of a node.
func (g *Graph) InEdges(id NodeID) []*Edge {
	g.mu.RLock()
	defer g.mu.RUnlock()
	out := make([]*Edge, len(g.inEdges[id]))
	copy(out, g.inEdges[id])
	return out
}

// Neighbours returns the nodes reachable from a node, optionally
// filtered by edge label.
func (g *Graph) Neighbours(id NodeID, label string) []*Node {
	g.mu.RLock()
	defer g.mu.RUnlock()
	var out []*Node
	for _, e := range g.out[id] {
		if label != "" && e.Label != label {
			continue
		}
		out = append(out, g.nodes[e.To])
	}
	return out
}

// NodeCount returns the number of nodes.
func (g *Graph) NodeCount() int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return len(g.nodes)
}

// EdgeCount returns the number of edges.
func (g *Graph) EdgeCount() int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return len(g.edges)
}

// RemoveEdge removes an edge by ID.
func (g *Graph) RemoveEdge(id EdgeID) bool {
	g.mu.Lock()
	defer g.mu.Unlock()
	e, ok := g.edges[id]
	if !ok {
		return false
	}
	g.out[e.From] = removeEdge(g.out[e.From], id)
	g.inEdges[e.To] = removeEdge(g.inEdges[e.To], id)
	delete(g.edges, id)
	return true
}

func removeEdge(list []*Edge, id EdgeID) []*Edge {
	out := list[:0]
	for _, e := range list {
		if e.ID != id {
			out = append(out, e)
		}
	}
	return out
}

// BFS performs a breadth-first traversal from a start node.
func (g *Graph) BFS(start NodeID, maxDepth int) []NodeID {
	g.mu.RLock()
	defer g.mu.RUnlock()
	if _, ok := g.nodes[start]; !ok {
		return nil
	}
	visited := map[NodeID]bool{start: true}
	order := []NodeID{start}
	type item struct {
		id    NodeID
		depth int
	}
	queue := []item{{start, 0}}
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		if cur.depth >= maxDepth {
			continue
		}
		for _, e := range g.out[cur.id] {
			if visited[e.To] {
				continue
			}
			visited[e.To] = true
			order = append(order, e.To)
			queue = append(queue, item{e.To, cur.depth + 1})
		}
	}
	return order
}

// DFS performs a depth-first traversal from a start node.
func (g *Graph) DFS(start NodeID, maxDepth int) []NodeID {
	g.mu.RLock()
	defer g.mu.RUnlock()
	if _, ok := g.nodes[start]; !ok {
		return nil
	}
	visited := map[NodeID]bool{}
	order := []NodeID{}
	var walk func(id NodeID, depth int)
	walk = func(id NodeID, depth int) {
		if visited[id] || depth > maxDepth {
			return
		}
		visited[id] = true
		order = append(order, id)
		for _, e := range g.out[id] {
			if !visited[e.To] {
				walk(e.To, depth+1)
			}
		}
	}
	walk(start, 0)
	return order
}

// Path is a route through the graph.
type Path struct {
	Nodes []NodeID
	Edges []*Edge
	Cost  float64
}

// ShortestPath finds the lowest-cost path from src to dst (Dijkstra).
func (g *Graph) ShortestPath(src, dst NodeID) (*Path, error) {
	g.mu.RLock()
	defer g.mu.RUnlock()
	if _, ok := g.nodes[src]; !ok {
		return nil, errors.New("source not found")
	}
	if _, ok := g.nodes[dst]; !ok {
		return nil, errors.New("target not found")
	}

	dist := map[NodeID]float64{src: 0}
	prev := map[NodeID]*Edge{}
	visited := map[NodeID]bool{}

	for {
		// pick min unvisited
		var best NodeID
		bestD := -1.0
		for id, d := range dist {
			if visited[id] {
				continue
			}
			if bestD < 0 || d < bestD {
				bestD = d
				best = id
			}
		}
		if bestD < 0 {
			break
		}
		if best == dst {
			break
		}
		visited[best] = true
		for _, e := range g.out[best] {
			w := e.Weight
			if w <= 0 {
				w = 1
			}
			nd := bestD + w
			if old, ok := dist[e.To]; !ok || nd < old {
				dist[e.To] = nd
				prev[e.To] = e
			}
		}
	}

	if _, ok := dist[dst]; !ok {
		return nil, errors.New("no path exists")
	}

	path := &Path{Cost: dist[dst]}
	cur := dst
	for cur != src {
		e := prev[cur]
		if e == nil {
			return nil, errors.New("no path exists")
		}
		path.Edges = append([]*Edge{e}, path.Edges...)
		path.Nodes = append([]NodeID{cur}, path.Nodes...)
		cur = e.From
	}
	path.Nodes = append([]NodeID{src}, path.Nodes...)
	return path, nil
}

// AllPaths returns all simple paths from src to dst up to maxDepth.
func (g *Graph) AllPaths(src, dst NodeID, maxDepth int) []*Path {
	g.mu.RLock()
	defer g.mu.RUnlock()
	var paths []*Path
	visited := map[NodeID]bool{src: true}
	var curPath *Path
	var walk func(id NodeID)
	curPath = &Path{Nodes: []NodeID{src}}
	walk = func(id NodeID) {
		if len(curPath.Nodes) > maxDepth {
			return
		}
		if id == dst {
			cp := &Path{Nodes: append([]NodeID(nil), curPath.Nodes...), Edges: append([]*Edge(nil), curPath.Edges...), Cost: curPath.Cost}
			paths = append(paths, cp)
			return
		}
		for _, e := range g.out[id] {
			if visited[e.To] {
				continue
			}
			visited[e.To] = true
			w := e.Weight
			if w <= 0 {
				w = 1
			}
			curPath.Nodes = append(curPath.Nodes, e.To)
			curPath.Edges = append(curPath.Edges, e)
			curPath.Cost += w
			walk(e.To)
			curPath.Nodes = curPath.Nodes[:len(curPath.Nodes)-1]
			curPath.Edges = curPath.Edges[:len(curPath.Edges)-1]
			curPath.Cost -= w
			visited[e.To] = false
		}
	}
	walk(src)
	return paths
}

// Query is a graph query specification.
type Query struct {
	StartID NodeID
	Labels  []string
	MaxDepth int
	Limit   int
}

// Execute runs a query, returning matching nodes.
func (g *Graph) Execute(q Query) []*Node {
	g.mu.RLock()
	defer g.mu.RUnlock()
	if _, ok := g.nodes[q.StartID]; !ok {
		return nil
	}
	labelSet := make(map[string]bool, len(q.Labels))
	for _, l := range q.Labels {
		labelSet[l] = true
	}
	depth := q.MaxDepth
	if depth <= 0 {
		depth = 1
	}
	visited := map[NodeID]bool{q.StartID: true}
	order := []NodeID{q.StartID}
	type it struct {
		id    NodeID
		depth int
	}
	queue := []it{{q.StartID, 0}}
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		if cur.depth >= depth {
			continue
		}
		for _, e := range g.out[cur.id] {
			if visited[e.To] {
				continue
			}
			if len(labelSet) > 0 && !labelSet[e.Label] {
				continue
			}
			visited[e.To] = true
			order = append(order, e.To)
			queue = append(queue, it{e.To, cur.depth + 1})
		}
	}
	if q.Limit > 0 && len(order) > q.Limit {
		order = order[:q.Limit]
	}
	out := make([]*Node, 0, len(order))
	for _, id := range order {
		out = append(out, g.nodes[id])
	}
	return out
}

// PageRank computes PageRank scores for all nodes.
func (g *Graph) PageRank(damping float64, iterations int) map[NodeID]float64 {
	g.mu.RLock()
	defer g.mu.RUnlock()

	n := len(g.nodes)
	if n == 0 {
		return nil
	}
	rank := make(map[NodeID]float64, n)
	for id := range g.nodes {
		rank[id] = 1.0 / float64(n)
	}
	for it := 0; it < iterations; it++ {
		next := make(map[NodeID]float64, n)
		for id := range g.nodes {
			next[id] = (1.0 - damping) / float64(n)
		}
		for id := range g.nodes {
			outdeg := len(g.out[id])
			if outdeg == 0 {
				continue
			}
			share := damping * rank[id] / float64(outdeg)
			for _, e := range g.out[id] {
				next[e.To] += share
			}
		}
		rank = next
	}
	return rank
}

// TopNodes returns the highest-ranked nodes.
func (g *Graph) TopNodes(rank map[NodeID]float64, k int) []NodeID {
	type pair struct {
		id NodeID
		r  float64
	}
	pairs := make([]pair, 0, len(rank))
	for id, r := range rank {
		pairs = append(pairs, pair{id, r})
	}
	sort.Slice(pairs, func(i, j int) bool { return pairs[i].r > pairs[j].r })
	out := make([]NodeID, 0, k)
	for i := 0; i < k && i < len(pairs); i++ {
		out = append(out, pairs[i].id)
	}
	return out
}

// ReasoningRule is a simple inference rule: if A -[rel]-> B
// and B -[rel2]-> C then A -[conclusion]-> C.
type ReasoningRule struct {
	Name      string
	Rel1      string
	Rel2      string
	Conclusion string
}

// Reasoner performs rule-based inference over the graph.
type Reasoner struct {
	graph *Graph
	rules []ReasoningRule
}

// NewReasoner creates a reasoner.
func NewReasoner(g *Graph) *Reasoner {
	return &Reasoner{graph: g}
}

// AddRule adds an inference rule.
func (r *Reasoner) AddRule(rule ReasoningRule) {
	r.rules = append(r.rules, rule)
}

// Infer returns new edges inferred by applying all rules.
func (r *Reasoner) Infer() []*Edge {
	g := r.graph
	var inferred []*Edge
	seen := map[string]bool{}

	for _, rule := range r.rules {
		for _, from := range g.BFS("", 0) {
			_ = from
			break
		}
		// apply rule to every node
		g.mu.RLock()
		ids := make([]NodeID, 0, len(g.nodes))
		for id := range g.nodes {
			ids = append(ids, id)
		}
		g.mu.RUnlock()

		for _, id := range ids {
			for _, e1 := range g.OutEdges(id) {
				if e1.Label != rule.Rel1 {
					continue
				}
				for _, e2 := range g.OutEdges(e1.To) {
					if e2.Label != rule.Rel2 {
						continue
					}
					key := string(id) + "|" + string(e2.To) + "|" + rule.Conclusion
					if seen[key] {
						continue
					}
					seen[key] = true
					inferred = append(inferred, &Edge{
						From:   id,
						To:     e2.To,
						Label:  rule.Conclusion,
						Weight: e1.Weight * e2.Weight,
						Props:  map[string]interface{}{"inferred": true, "rule": rule.Name},
					})
				}
			}
		}
	}
	return inferred
}

// Subgraph extracts a subgraph containing the given nodes and the
// edges between them.
func (g *Graph) Subgraph(ids []NodeID) *Graph {
	sub := NewGraph()
	want := make(map[NodeID]bool, len(ids))
	g.mu.RLock()
	defer g.mu.RUnlock()
	for _, id := range ids {
		if n, ok := g.nodes[id]; ok {
			want[id] = true
			sub.nodes[id] = n
		}
	}
	for _, e := range g.edges {
		if want[e.From] && want[e.To] {
			sub.edges[e.ID] = e
			sub.out[e.From] = append(sub.out[e.From], e)
			sub.inEdges[e.To] = append(sub.inEdges[e.To], e)
		}
	}
	return sub
}

func itoa64(n int64) string {
	if n == 0 {
		return "0"
	}
	var buf [20]byte
	i := len(buf)
	neg := n < 0
	if neg {
		n = -n
	}
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}