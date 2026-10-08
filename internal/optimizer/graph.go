package optimizer

import (
	"container/list"
	"math"
	"sort"
)

// Graph represents a computation graph for optimization.
type Graph struct {
	Nodes     map[string]*Node
	Constants map[string]float64
	Output    string
}

// Node represents a single operation in the graph.
type Node struct {
	Name     string
	Op       string
	Inputs   []string
	Value    float64
	Computed bool
}

// NewGraph creates an empty computation graph.
func NewGraph() *Graph {
	return &Graph{
		Nodes:     make(map[string]*Node),
		Constants: make(map[string]float64),
	}
}

// AddNode adds a node to the graph.
func (g *Graph) AddNode(name, op string, inputs []string) {
	node := &Node{
		Name:   name,
		Op:     op,
		Inputs: inputs,
	}
	if op == "constant" {
		if val, ok := g.Constants[name]; ok {
			node.Value = val
			node.Computed = true
		}
	}
	g.Nodes[name] = node
}

// TopologicalSort returns nodes in topological order.
func (g *Graph) TopologicalSort() []*Node {
	inDegree := make(map[string]int)
	for name := range g.Nodes {
		inDegree[name] = 0
	}
	for _, node := range g.Nodes {
		for range node.Inputs {
			inDegree[node.Name]++
		}
	}

	queue := list.New()
	for name, degree := range inDegree {
		if degree == 0 {
			queue.PushBack(name)
		}
	}

	var order []*Node
	for queue.Len() > 0 {
		elem := queue.Front()
		queue.Remove(elem)
		name := elem.Value.(string)
		order = append(order, g.Nodes[name])

		for _, node := range g.Nodes {
			for _, input := range node.Inputs {
				if input == name {
					inDegree[node.Name]--
					if inDegree[node.Name] == 0 {
						queue.PushBack(node.Name)
					}
				}
			}
		}
	}

	return order
}

// ConstantFolding replaces constant operations with their computed values.
func (g *Graph) ConstantFolding() {
	for range 4 {
		changed := false
		for _, node := range g.Nodes {
			if node.Computed {
				continue
			}
			if node.Op == "constant" {
				node.Computed = true
				node.Value = g.Constants[node.Name]
				changed = true
				continue
			}
			if !allInputsComputed(node.Inputs, g.Nodes) {
				continue
			}
			inputs := make([]float64, len(node.Inputs))
			for i, input := range node.Inputs {
				inputs[i] = g.Nodes[input].Value
			}
			value, ok := evaluate(node.Op, inputs)
			if ok {
				node.Computed = true
				node.Value = value
				changed = true
			}
		}
		if !changed {
			break
		}
	}
}

// DeadCodeElimination removes nodes that are not reachable from the output.
func (g *Graph) DeadCodeElimination() {
	if g.Output == "" {
		g.Nodes = make(map[string]*Node)
		return
	}

	reachable := make(map[string]bool)
	var dfs func(string)
	dfs = func(name string) {
		if reachable[name] {
			return
		}
		reachable[name] = true
		node := g.Nodes[name]
		for _, input := range node.Inputs {
			dfs(input)
		}
	}
	dfs(g.Output)

	for name := range g.Nodes {
		if !reachable[name] {
			delete(g.Nodes, name)
		}
	}
}

// OperatorFusion merges compatible operations.
func (g *Graph) OperatorFusion() {
	for _, node := range g.Nodes {
		if node.Op != "add" {
			continue
		}
		for _, inputName := range node.Inputs {
			input := g.Nodes[inputName]
			if input.Op == "matmul" {
				input.Op = "fused_matmul_add"
				node.Op = "identity"
				node.Inputs = nil
				break
			}
		}
	}
}

// allInputsComputed checks if all input nodes have been computed.
func allInputsComputed(inputs []string, nodes map[string]*Node) bool {
	for _, input := range inputs {
		if node, exists := nodes[input]; !exists || !node.Computed {
			return false
		}
	}
	return true
}

// evaluate computes the result of an operation.
func evaluate(op string, inputs []float64) (float64, bool) {
	switch op {
	case "add":
		if len(inputs) == 2 {
			return inputs[0] + inputs[1], true
		}
	case "mul":
		if len(inputs) == 2 {
			return inputs[0] * inputs[1], true
		}
	case "sub":
		if len(inputs) == 2 {
			return inputs[0] - inputs[1], true
		}
	case "div":
		if len(inputs) == 2 && inputs[1] != 0 {
			return inputs[0] / inputs[1], true
		}
	case "neg":
		if len(inputs) == 1 {
			return -inputs[0], true
		}
	case "relu":
		if len(inputs) == 1 {
			return math.Max(0, inputs[0]), true
		}
	case "sigmoid":
		if len(inputs) == 1 {
			return 1.0 / (1.0 + math.Exp(-inputs[0])), true
		}
	case "tanh":
		if len(inputs) == 1 {
			return math.Tanh(inputs[0]), true
		}
	case "exp":
		if len(inputs) == 1 {
			return math.Exp(inputs[0]), true
		}
	case "log":
		if len(inputs) == 1 && inputs[0] > 0 {
			return math.Log(inputs[0]), true
		}
	case "sqrt":
		if len(inputs) == 1 && inputs[0] >= 0 {
			return math.Sqrt(inputs[0]), true
		}
	case "pow":
		if len(inputs) == 2 {
			return math.Pow(inputs[0], inputs[1]), true
		}
	}
	return 0, false
}

// CommonSubexpressionElimination removes duplicate computations.
// Iteration is over sorted node names so the pass is
// deterministic: for a duplicate pair, the
// lexicographically-first name is always kept.
func (g *Graph) CommonSubexpressionElimination() {
	exprMap := make(map[string]string)
	names := make([]string, 0, len(g.Nodes))
	for name := range g.Nodes {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		node := g.Nodes[name]
		if node.Op == "constant" || node.Computed {
			continue
		}
		key := node.Op + "|"
		for _, input := range node.Inputs {
			key += input + ","
		}
		if existing, exists := exprMap[key]; exists {
			delete(g.Nodes, name)
			for _, n := range g.Nodes {
				for i, input := range n.Inputs {
					if input == name {
						n.Inputs[i] = existing
					}
				}
			}
		} else {
			exprMap[key] = name
		}
	}
}

// MemoryReusePlanning attempts to reuse buffers for temporary values.
func (g *Graph) MemoryReusePlanning() map[string]string {
	reuseMap := make(map[string]string)
	used := make(map[string]bool)
	order := g.TopologicalSort()
	for _, node := range order {
		if node.Op == "constant" || node.Computed {
			continue
		}
		for _, input := range node.Inputs {
			if !used[input] {
				reuseMap[input] = node.Name
				used[input] = true
				break
			}
		}
	}
	return reuseMap
}

// Simplify performs all optimizations.
func (g *Graph) Simplify() {
	g.ConstantFolding()
	g.DeadCodeElimination()
	g.CommonSubexpressionElimination()
	g.OperatorFusion()
}

// SortTopological returns a sorted slice of node names.
func (g *Graph) SortTopological() []string {
	nodes := g.TopologicalSort()
	names := make([]string, len(nodes))
	for i, n := range nodes {
		names[i] = n.Name
	}
	sort.Strings(names)
	return names
}
