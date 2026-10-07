package ir

import (
	"fmt"
)

// DominatorTree represents the dominator tree of a CFG.
type DominatorTree struct {
	IDom    map[int]int
	DomTree map[int][]int
}

// ComputeDominators computes the immediate dominators of a CFG.
func ComputeDominators(cfg *CFG) *DominatorTree {
	if cfg == nil || len(cfg.Nodes) == 0 {
		return &DominatorTree{IDom: make(map[int]int), DomTree: make(map[int][]int)}
	}

	idom := make(map[int]int)
	for id := range cfg.Nodes {
		if id == cfg.Entry {
			idom[id] = id
		} else {
			idom[id] = 0
		}
	}

	changed := true
	for changed {
		changed = false
		for id, node := range cfg.Nodes {
			if id == cfg.Entry {
				continue
			}
			preds := node.Predecessors
			if len(preds) == 0 {
				continue
			}
			newIdom := preds[0]
			for _, p := range preds[1:] {
				if idom[p] != 0 && (idom[newIdom] == 0 || intersect(idom[p], idom[newIdom], idom) != newIdom) {
					newIdom = p
				}
			}
			if idom[id] != newIdom {
				idom[id] = newIdom
				changed = true
			}
		}
	}

	domTree := make(map[int][]int)
	for id, parent := range idom {
		if id != parent && parent != 0 {
			domTree[parent] = append(domTree[parent], id)
		}
	}

	return &DominatorTree{IDom: idom, DomTree: domTree}
}

func intersect(b1, b2 int, idom map[int]int) int {
	for b1 != b2 {
		for b1 > b2 {
			b1 = idom[b1]
		}
		for b2 > b1 {
			b2 = idom[b2]
		}
	}
	return b1
}

// Dominates returns true if b1 dominates b2.
func (d *DominatorTree) Dominates(b1, b2 int) bool {
	if b1 == b2 {
		return true
	}
	current := b2
	for current != 0 && current != d.IDom[current] {
		if current == b1 {
			return true
		}
		current = d.IDom[current]
	}
	return current == b1
}

// Loop represents a natural loop.
type Loop struct {
	Header  int
	Members map[int]bool
}

// FindLoops identifies natural loops in a CFG.
func FindLoops(cfg *CFG) []*Loop {
	dom := ComputeDominators(cfg)
	if dom == nil {
		return nil
	}

	loops := make([]*Loop, 0)
	visited := make(map[int]bool)

	for id, node := range cfg.Nodes {
		for _, succ := range node.Successors {
			if dom.IDom[succ] != id {
				continue
			}
			header := id
			members := map[int]bool{header: true}
			var stack []int
			stack = append(stack, succ)
			for len(stack) > 0 {
				cur := stack[len(stack)-1]
				stack = stack[:len(stack)-1]
				if visited[cur] && cur != succ {
					continue
				}
				visited[cur] = true
				members[cur] = true
				if cfg.Nodes[cur] != nil {
					for _, pred := range cfg.Nodes[cur].Predecessors {
						if !members[pred] {
							stack = append(stack, pred)
						}
					}
				}
			}
			if len(members) > 1 {
				loops = append(loops, &Loop{Header: header, Members: members})
			}
		}
	}

	return loops
}

// LoopHierarchy builds a parent relationship among loops.
func LoopHierarchy(loops []*Loop) map[int]int {
	parent := make(map[int]int)
	for i, l := range loops {
		for j, other := range loops {
			if i != j && other.Members[l.Header] {
				if _, ok := parent[l.Header]; !ok {
					parent[l.Header] = other.Header
				}
			}
		}
	}
	return parent
}

// Metadata represents debug and profiling metadata.
type Metadata struct {
	DebugInfo   map[string]string
	ProfileData map[string]float64
}

// NewMetadata creates a new metadata container.
func NewMetadata() *Metadata {
	return &Metadata{
		DebugInfo:   make(map[string]string),
		ProfileData: make(map[string]float64),
	}
}

// TypePromotion defines promotion rules between types.
var TypePromotion = map[string]string{
	"int32":  "int64",
	"int64":  "int64",
	"float32": "float64",
	"float64": "float64",
}

// PromoteType promotes a type according to the promotion table.
func PromoteType(from string) string {
	if to, ok := TypePromotion[from]; ok {
		return to
	}
	return from
}

// ShapePropagator propagates tensor shapes through operations.
type ShapePropagator struct{}

// NewShapePropagator creates a new propagator.
func NewShapePropagator() *ShapePropagator {
	return &ShapePropagator{}
}

// Propagate returns the output shape for an operation.
func (s *ShapePropagator) Propagate(op string, inputs []Shape) Shape {
	if len(inputs) == 0 {
		return Shape{}
	}
	switch op {
	case "add", "sub", "mul", "div":
		return inputs[0]
	case "matmul":
		if len(inputs) >= 2 && len(inputs[0]) >= 1 && len(inputs[1]) >= 1 {
			out := make(Shape, len(inputs[0])-1)
			copy(out, inputs[0][:len(inputs[0])-1])
			out = append(out, inputs[1][len(inputs[1])-1])
			return out
		}
		return Shape{}
	default:
		return Shape{}
	}
}

func (m *Metadata) String() string {
	return fmt.Sprintf("metadata{debug=%d,profile=%d}", len(m.DebugInfo), len(m.ProfileData))
}
