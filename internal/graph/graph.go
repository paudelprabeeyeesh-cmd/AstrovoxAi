package graph

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
)

// Node represents a node in a computation graph.
type Node struct {
	ID    int
	Op    string
	Input []int
	Shape []int
	DType string
}

// Edge represents a connection between nodes.
type Edge struct {
	From int
	To   int
}

// Graph represents a computation graph.
type Graph struct {
	Nodes map[int]*Node
	Edges []Edge
}

// NewGraph creates an empty computation graph.
func NewGraph() *Graph {
	return &Graph{
		Nodes: make(map[int]*Node),
	}
}

// AddNode adds a node to the graph.
func (g *Graph) AddNode(id int, op string, shape []int, dtype string) *Node {
	node := &Node{
		ID:    id,
		Op:    op,
		Shape: shape,
		DType: dtype,
	}
	g.Nodes[id] = node
	return node
}

// AddEdge adds an edge to the graph.
func (g *Graph) AddEdge(from, to int) {
	g.Edges = append(g.Edges, Edge{From: from, To: to})
	if fromNode, ok := g.Nodes[from]; ok {
		fromNode.Input = append(fromNode.Input, to)
	}
}

// ToDOT writes the graph in DOT format for visualization.
func (g *Graph) ToDOT(w io.Writer) error {
	_, err := fmt.Fprintln(w, "digraph astrovox {")
	if err != nil {
		return err
	}
	for _, node := range g.Nodes {
		label := fmt.Sprintf("%d: %s", node.ID, node.Op)
		_, err = fmt.Fprintf(w, "  n%d [label=\"%s\"];\n", node.ID, label)
		if err != nil {
			return err
		}
	}
	for _, edge := range g.Edges {
		_, err = fmt.Fprintf(w, "  n%d -> n%d;\n", edge.From, edge.To)
		if err != nil {
			return err
		}
	}
	_, err = fmt.Fprintln(w, "}")
	return err
}

// ToJSON serializes the graph to JSON.
func (g *Graph) ToJSON() ([]byte, error) {
	type jsonEdge struct {
		From int `json:"from"`
		To   int `json:"to"`
	}
	type jsonNode struct {
		ID    int    `json:"id"`
		Op    string `json:"op"`
		Input []int  `json:"input"`
		Shape []int  `json:"shape"`
		DType string `json:"dtype"`
	}
	nodes := make([]jsonNode, 0, len(g.Nodes))
	for _, node := range g.Nodes {
		nodes = append(nodes, jsonNode{
			ID:    node.ID,
			Op:    node.Op,
			Input: node.Input,
			Shape: node.Shape,
			DType: node.DType,
		})
	}
	edges := make([]jsonEdge, len(g.Edges))
	for i, edge := range g.Edges {
		edges[i] = jsonEdge{From: edge.From, To: edge.To}
	}
	payload := map[string]interface{}{
		"nodes": nodes,
		"edges": edges,
	}
	return json.Marshal(payload)
}

// LoadGraph loads a graph from a DOT file.
func LoadGraph(path string) (*Graph, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	graph := NewGraph()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if strings.HasPrefix(line, "n") && strings.Contains(line, "->") {
			parts := strings.Split(line, "->")
			if len(parts) == 2 {
				var from, to int
				fmt.Sscanf(strings.TrimSpace(parts[0]), "n%d", &from)
				fmt.Sscanf(strings.TrimSpace(parts[1]), "n%d", &to)
				graph.AddEdge(from, to)
			}
		}
	}
	return graph, scanner.Err()
}

// Visualize generates a DOT representation.
func (g *Graph) Visualize() string {
	var sb strings.Builder
	_ = g.ToDOT(&sb)
	return sb.String()
}
