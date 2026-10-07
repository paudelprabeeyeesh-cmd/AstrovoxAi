package ir

// CFGNode represents a control flow graph node.
type CFGNode struct {
	ID       int
	Label    string
	Successors []int
	Predecessors []int
}

// CFG represents a control flow graph.
type CFG struct {
	Nodes map[int]*CFGNode
	Entry int
	Exit  int
}

// NewCFG creates a new control flow graph.
func NewCFG() *CFG {
	return &CFG{Nodes: make(map[int]*CFGNode)}
}

// AddNode adds a CFG node.
func (c *CFG) AddNode(n *CFGNode) {
	c.Nodes[n.ID] = n
}

// AddEdge adds a control flow edge.
func (c *CFG) AddEdge(from, to int) {
	if from == to {
		return
	}
	if c.Nodes[from] == nil || c.Nodes[to] == nil {
		return
	}
	c.Nodes[from].Successors = append(c.Nodes[from].Successors, to)
	c.Nodes[to].Predecessors = append(c.Nodes[to].Predecessors, from)
}
