package ir

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sort"
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
	NodeKindPhi      NodeKind = "phi"
	NodeKindSwitch   NodeKind = "switch"
	NodeKindAlloca   NodeKind = "alloca"
	NodeKindLoad     NodeKind = "load"
	NodeKindStore    NodeKind = "store"
)

// DataType represents a supported tensor/data type.
type DataType string

const (
	DataTypeFloat32 DataType = "float32"
	DataTypeFloat64 DataType = "float64"
	DataTypeInt32   DataType = "int32"
	DataTypeInt64   DataType = "int64"
	DataTypeBool    DataType = "bool"
	DataTypeUint8   DataType = "uint8"
)

// Shape describes tensor dimensions.
type Shape []int

// String returns a human-readable shape.
func (s Shape) String() string {
	var parts []string
	for _, d := range s {
		if d < 0 {
			parts = append(parts, "?")
		} else {
			parts = append(parts, fmt.Sprintf("%d", d))
		}
	}
	return "[" + join(parts, "x") + "]"
}

func join(parts []string, sep string) string {
	switch len(parts) {
	case 0:
		return ""
	case 1:
		return parts[0]
	case 2:
		return parts[0] + sep + parts[1]
	default:
		b := bytes.NewBufferString(parts[0])
		for _, p := range parts[1:] {
			b.WriteString(sep)
			b.WriteString(p)
		}
		return b.String()
	}
}

// Rank returns the number of dimensions.
func (s Shape) Rank() int { return len(s) }

// NumElements returns total element count, or -1 if unknown.
func (s Shape) NumElements() int {
	if len(s) == 0 {
		return 1
	}
	n := 1
	for _, d := range s {
		if d < 0 {
			return -1
		}
		n *= d
	}
	return n
}

// IsScalar reports whether the shape represents a scalar.
func (s Shape) IsScalar() bool { return len(s) == 0 }

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

// Clone returns a deep copy of the node.
func (n *Node) Clone() *Node {
	return &Node{
		ID:       n.ID,
		Kind:     n.Kind,
		Op:       n.Op,
		Inputs:   append([]int64(nil), n.Inputs...),
		Outputs:  append([]int64(nil), n.Outputs...),
		Shape:    append(Shape(nil), n.Shape...),
		DType:    n.DType,
		Attrs:    cloneMap(n.Attrs),
		Metadata: cloneStringMap(n.Metadata),
	}
}

func cloneMap(m map[string]interface{}) map[string]interface{} {
	if m == nil {
		return nil
	}
	out := make(map[string]interface{}, len(m))
	for k, v := range m {
		out[k] = v
	}
	return out
}

func cloneStringMap(m map[string]string) map[string]string {
	if m == nil {
		return nil
	}
	out := make(map[string]string, len(m))
	for k, v := range m {
		out[k] = v
	}
	return out
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

// RemoveNode deletes a node by ID.
func (g *Graph) RemoveNode(id int64) {
	delete(g.Nodes, id)
}

// GetNode returns a node by ID or nil.
func (g *Graph) GetNode(id int64) *Node {
	return g.Nodes[id]
}

// NodeCount returns the number of nodes.
func (g *Graph) NodeCount() int { return len(g.Nodes) }

// GraphBuilder provides a fluent API to construct graphs.
type GraphBuilder struct {
	g *Graph
}

// NewGraphBuilder returns a new builder.
func NewGraphBuilder() *GraphBuilder {
	return &GraphBuilder{g: NewGraph()}
}

// Build returns the constructed graph.
func (b *GraphBuilder) Build() *Graph { return b.g }

// Add adds a node to the builder graph.
func (b *GraphBuilder) Add(n *Node) int64 {
	return b.g.AddNode(n)
}

// Constant adds a constant node.
func (b *GraphBuilder) Constant(name string, value interface{}, shape Shape, dtype DataType) int64 {
	n := &Node{
		Kind:  NodeKindConstant,
		Op:    name,
		Shape: shape,
		DType: dtype,
		Attrs: map[string]interface{}{"value": value},
	}
	if shape == nil {
		n.Shape = Shape{}
	}
	return b.Add(n)
}

// Variable adds a variable node.
func (b *GraphBuilder) Variable(name string, shape Shape, dtype DataType) int64 {
	n := &Node{
		Kind:  NodeKindVariable,
		Op:    name,
		Shape: shape,
		DType: dtype,
	}
	if shape == nil {
		n.Shape = Shape{}
	}
	return b.Add(n)
}

// Call adds a call node.
func (b *GraphBuilder) Call(callee string, inputs []int64, shape Shape, dtype DataType) int64 {
	n := &Node{
		Kind:   NodeKindCall,
		Op:     callee,
		Inputs: inputs,
		Shape:  shape,
		DType:  dtype,
	}
	if shape == nil {
		n.Shape = Shape{}
	}
	return b.Add(n)
}

// SetOutput sets graph outputs.
func (b *GraphBuilder) SetOutput(ids ...int64) {
	b.g.Output = append([]int64(nil), ids...)
}

// ValidateGraph checks graph integrity.
func (g *Graph) ValidateGraph() error {
	if g == nil {
		return fmt.Errorf("graph is nil")
	}
	if len(g.Nodes) == 0 && len(g.Output) == 0 {
		return nil
	}
	ids := make(map[int64]bool)
	for id := range g.Nodes {
		if id <= 0 {
			return fmt.Errorf("invalid node id: %d", id)
		}
		if ids[id] {
			return fmt.Errorf("duplicate node id: %d", id)
		}
		ids[id] = true
	}
	for _, out := range g.Output {
		if _, ok := g.Nodes[out]; !ok {
			return fmt.Errorf("output node %d not in graph", out)
		}
	}
	for _, n := range g.Nodes {
		for _, in := range n.Inputs {
			if _, ok := g.Nodes[in]; !ok {
				return fmt.Errorf("node %d references missing input %d", n.ID, in)
			}
		}
	}
	if hasCycle(g) {
		return fmt.Errorf("graph contains a cycle")
	}
	return nil
}

func hasCycle(g *Graph) bool {
	visited := make(map[int64]bool)
	var recStack map[int64]bool
	var dfs func(id int64) bool
	recStack = make(map[int64]bool)
	dfs = func(id int64) bool {
		visited[id] = true
		recStack[id] = true
		n := g.Nodes[id]
		for _, in := range n.Inputs {
			if !visited[in] {
				if dfs(in) {
					return true
				}
			} else if recStack[in] {
				return true
			}
		}
		recStack[id] = false
		return false
	}
	for id := range g.Nodes {
		if !visited[id] {
			if dfs(id) {
				return true
			}
		}
	}
	return false
}

// InferShape attempts to infer unknown shapes using simple rules.
func (g *Graph) InferShape() error {
	order := g.TopologicalSort()
	for _, n := range order {
		if len(n.Shape) > 0 {
			continue
		}
		switch n.Kind {
		case NodeKindConstant:
			if v, ok := n.Attrs["value"]; ok {
				switch val := v.(type) {
				case []interface{}:
					n.Shape = Shape{len(val)}
				case []float64:
					n.Shape = Shape{len(val)}
				case []int:
					n.Shape = Shape{len(val)}
				case float64, int, int64, string:
					n.Shape = Shape{}
				default:
					n.Shape = Shape{}
				}
			} else {
				n.Shape = Shape{}
			}
		case NodeKindVariable:
			n.Shape = Shape{-1}
		case NodeKindCall:
			n.Shape = Shape{-1}
		case NodeKindReturn, NodeKindBranch, NodeKindLoop:
			n.Shape = Shape{}
		case NodeKindPhi:
			for _, in := range n.Inputs {
				if src, ok := g.Nodes[in]; ok && len(src.Shape) > 0 {
					n.Shape = append(Shape(nil), src.Shape...)
					break
				}
			}
		case NodeKindAlloca, NodeKindLoad:
			n.Shape = Shape{-1}
		case NodeKindStore:
			n.Shape = Shape{}
		}
	}
	return nil
}

// InferType attempts to infer unknown dtypes using simple rules.
func (g *Graph) InferType() error {
	order := g.TopologicalSort()
	for _, n := range order {
		if n.DType != "" {
			continue
		}
		switch n.Kind {
		case NodeKindConstant:
			if _, ok := n.Attrs["value"].(float64); ok {
				n.DType = DataTypeFloat64
			} else {
				n.DType = DataTypeFloat32
			}
		case NodeKindVariable, NodeKindCall, NodeKindLoad:
			n.DType = DataTypeFloat32
		case NodeKindPhi:
			for _, in := range n.Inputs {
				if src, ok := g.Nodes[in]; ok && src.DType != "" {
					n.DType = src.DType
					break
				}
			}
		case NodeKindReturn, NodeKindBranch, NodeKindLoop, NodeKindStore:
			n.DType = DataTypeFloat32
		}
	}
	return nil
}

// EnrichMetadata adds default metadata to nodes.
func (g *Graph) EnrichMetadata() {
	for _, n := range g.Nodes {
		if n.Metadata == nil {
			n.Metadata = make(map[string]string)
		}
		if _, ok := n.Metadata["kind"]; !ok {
			n.Metadata["kind"] = string(n.Kind)
		}
		if _, ok := n.Metadata["op"]; !ok && n.Op != "" {
			n.Metadata["op"] = n.Op
		}
		if _, ok := n.Metadata["shape"]; !ok && len(n.Shape) > 0 {
			n.Metadata["shape"] = n.Shape.String()
		}
		if _, ok := n.Metadata["dtype"]; !ok && n.DType != "" {
			n.Metadata["dtype"] = string(n.DType)
		}
		if _, ok := n.Metadata["inputs"]; !ok && len(n.Inputs) > 0 {
			var ids []string
			for _, in := range n.Inputs {
				ids = append(ids, fmt.Sprintf("%d", in))
			}
			n.Metadata["inputs"] = join(ids, ",")
		}
	}
}

// TopologicalSort returns nodes in topological order.
func (g *Graph) TopologicalSort() []*Node {
	inDegree := make(map[int64]int)
	children := make(map[int64][]int64)
	for id := range g.Nodes {
		inDegree[id] = 0
		children[id] = nil
	}
	for _, node := range g.Nodes {
		for _, in := range node.Inputs {
			inDegree[node.ID]++
			children[in] = append(children[in], node.ID)
		}
	}

	var queue []int64
	for id, deg := range inDegree {
		if deg == 0 {
			queue = append(queue, id)
		}
	}
	sort.Slice(queue, func(i, j int) bool { return queue[i] < queue[j] })

	var order []*Node
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		order = append(order, g.Nodes[cur])
		for _, child := range children[cur] {
			deg := inDegree[child] - 1
			inDegree[child] = deg
			if deg == 0 {
				queue = append(queue, child)
			}
		}
	}
	if len(order) != len(g.Nodes) {
		var ids []int64
		for id := range g.Nodes {
			ids = append(ids, id)
		}
		sort.Slice(ids, func(i, j int) bool { return ids[i] < ids[j] })
		for _, id := range ids {
			order = append(order, g.Nodes[id])
		}
	}
	return order
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
	ids := make([]int64, 0, len(g.Nodes))
	for id := range g.Nodes {
		ids = append(ids, id)
	}
	sort.Slice(ids, func(i, j int) bool { return ids[i] < ids[j] })
	for _, id := range ids {
		n := g.Nodes[id]
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

// UnmarshalJSON implements json.Unmarshaler for Graph.
func (g *Graph) UnmarshalJSON(data []byte) error {
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
	var aux struct {
		Nodes  []jsonNode
		Output []int64
	}
	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}
	*g = *NewGraph()
	g.Output = append(g.Output, aux.Output...)
	for _, n := range aux.Nodes {
		g.Nodes[n.ID] = &Node{
			ID:       n.ID,
			Kind:     n.Kind,
			Op:       n.Op,
			Inputs:   n.Inputs,
			Outputs:  n.Outputs,
			Shape:    n.Shape,
			DType:    n.DType,
			Attrs:    n.Attrs,
			Metadata: n.Metadata,
		}
		if n.ID > idCounter {
			idCounter = n.ID
		}
	}
	return nil
}

// WriteGraphviz writes a Graphviz DOT representation of the graph.
func (g *Graph) WriteGraphviz(w io.Writer) error {
	_, err := fmt.Fprintln(w, "digraph astrovox {")
	if err != nil {
		return err
	}
	_, err = fmt.Fprintln(w, "  rankdir=TB;")
	if err != nil {
		return err
	}
	_, err = fmt.Fprintln(w, "  node [style=filled,fontname=\"Helvetica\"];")
	if err != nil {
		return err
	}
	for _, n := range g.Nodes {
		label := fmt.Sprintf("%s_%d", n.Kind, n.ID)
		if n.Op != "" {
			label = fmt.Sprintf("%s_%d (%s)", n.Kind, n.ID, n.Op)
		}
		shape := "box"
		color := "lightgrey"
		switch n.Kind {
		case NodeKindConstant:
			shape = "ellipse"
			color = "lightblue"
		case NodeKindVariable:
			shape = "ellipse"
			color = "lightgreen"
		case NodeKindCall:
			shape = "hexagon"
			color = "orange"
		case NodeKindLoop, NodeKindBranch, NodeKindReturn:
			shape = "diamond"
			color = "lightyellow"
		case NodeKindPhi, NodeKindSwitch, NodeKindAlloca, NodeKindLoad, NodeKindStore:
			shape = "note"
			color = "lightpink"
		}
		_, err = fmt.Fprintf(w, "  n%d [label=\"%s\", shape=%s, fillcolor=\"%s\"];\n", n.ID, label, shape, color)
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

// WriteGraphvizToFile writes DOT to a file path.
func (g *Graph) WriteGraphvizToFile(path string) error {
	f, err := createFile(path)
	if err != nil {
		return err
	}
	defer f.Close()
	return g.WriteGraphviz(f)
}

var idCounter int64

func nextID() int64 {
	idCounter++
	return idCounter
}

// ResetIDCounter resets the global ID counter (for tests).
func ResetIDCounter() { idCounter = 0 }

func createFile(path string) (*os.File, error) {
	// minimal helper to avoid import in some builds; fallback to os.Create
	return os.Create(path)
}
