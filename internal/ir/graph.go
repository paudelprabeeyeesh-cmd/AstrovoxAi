package ir

import (
	"encoding/json"
	"fmt"
	"io"
)

// NodeKind identifies the type of an IR node.
type NodeKind string

const (
	NodeKindConstant NodeKind = "constant"
	NodeKindVariable NodeKind = "variable"
	NodeKindFunction NodeKind = "function"
	NodeKindLoop     NodeKind = "loop"
	NodeKindBranch   NodeKind = "branch"
	NodeKindReturn   NodeKind = "return"
	NodeKindCall     NodeKind = "call"
)

// DataType represents a supported tensor/data type.
type DataType string

const (
	DataTypeFloat32 DataType = "float32"
	DataTypeFloat64 DataType = "float64"
	DataTypeInt32   DataType = "int32"
	DataTypeInt64   DataType = "int64"
	DataTypeBool    DataType = "bool"
)

// Shape describes tensor dimensions.
type Shape []int

// Node is a single node in the Astrovox IR graph.
type Node struct {
	ID       int64
	Kind     NodeKind
	Op       string
	Inputs   []int64
	Outputs  []int64
	Shape    Shape
	DType    DataType
	Attrs    map[string]interface{}
	Metadata map[string]string
}

// Graph is the top-level IR container.
type Graph struct {
	Nodes  map[int64]*Node
	Output []int64
}

// NewGraph creates an empty IR graph.
func NewGraph() *Graph {
	return &Graph{
		Nodes:  make(map[int64]*Node),
		Output: []int64{},
	}
}

// AddNode inserts a node and assigns its ID.
func (g *Graph) AddNode(n *Node) int64 {
	if n.ID == 0 {
		n.ID = nextID()
	}
	g.Nodes[n.ID] = n
	return n.ID
}

// MarshalJSON implements json.Marshaler for Graph.
func (g *Graph) MarshalJSON() ([]byte, error) {
	type jsonNode struct {
		ID       int64
		Kind     NodeKind
		Op       string
		Inputs   []int64
		Outputs  []int64
		Shape    Shape
		DType    DataType
		Attrs    map[string]interface{}
		Metadata map[string]string
	}
	nodes := make([]jsonNode, 0, len(g.Nodes))
	for _, n := range g.Nodes {
		nodes = append(nodes, jsonNode{
			ID:       n.ID,
			Kind:     n.Kind,
			Op:       n.Op,
			Inputs:   n.Inputs,
			Outputs:  n.Outputs,
			Shape:    n.Shape,
			DType:    n.DType,
			Attrs:    n.Attrs,
			Metadata: n.Metadata,
		})
	}
	return json.Marshal(map[string]interface{}{
		"nodes":  nodes,
		"output": g.Output,
	})
}

// WriteGraphviz writes a Graphviz DOT representation of the graph.
func (g *Graph) WriteGraphviz(w io.Writer) error {
	_, err := fmt.Fprintln(w, "digraph astrovox {")
	if err != nil {
		return err
	}
	for _, n := range g.Nodes {
		label := fmt.Sprintf("%s_%d", n.Kind, n.ID)
		if n.Op != "" {
			label = fmt.Sprintf("%s_%d (%s)", n.Kind, n.ID, n.Op)
		}
		_, err = fmt.Fprintf(w, "  n%d [label=\"%s\"];\n", n.ID, label)
		if err != nil {
			return err
		}
		for _, in := range n.Inputs {
			_, err = fmt.Fprintf(w, "  n%d -> n%d;\n", in, n.ID)
			if err != nil {
				return err
			}
		}
	}
	_, err = fmt.Fprintln(w, "}")
	return err
}

var idCounter int64

func nextID() int64 {
	idCounter++
	return idCounter
}
