package graph

import (
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Optimizer applies graph-level optimizations:
// constant folding, dead code elimination, and
// elementwise operator fusion.
type Optimizer struct {
	MaxPasses     int
	EnableFold    bool
	EnableDCE     bool
	EnableFusion  bool
	passesRun     int
	nodesRemoved  int
	nodesFused    int
}

// NewOptimizer creates an optimizer with default passes.
func NewOptimizer() *Optimizer {
	return &Optimizer{
		MaxPasses:    10,
		EnableFold:   true,
		EnableDCE:    true,
		EnableFusion: true,
	}
}

// Stats returns optimization statistics.
func (o *Optimizer) Stats() (passes, removed, fused int) {
	return o.passesRun, o.nodesRemoved, o.nodesFused
}

// Optimize runs the enabled passes to a fixpoint.
func (o *Optimizer) Optimize(g *Graph) error {
	if g == nil {
		return errors.New(errors.CodeInvalidArgument, "nil graph")
	}
	for pass := 0; pass < o.MaxPasses; pass++ {
		changed := false
		if o.EnableFold {
			if c, err := o.constantFold(g); err != nil {
				return err
			} else if c {
				changed = true
			}
		}
		if o.EnableDCE {
			if c, err := o.deadCodeElimination(g); err != nil {
				return err
			} else if c {
				changed = true
			}
		}
		if o.EnableFusion {
			if c, err := o.fuseElementwise(g); err != nil {
				return err
			} else if c {
				changed = true
			}
		}
		o.passesRun++
		if !changed {
			break
		}
	}
	return nil
}

// constantFold evaluates nodes whose inputs are all
// constant tensors. Constants are declared via node
// attributes under "const" holding []*tensor.Tensor.
func (o *Optimizer) constantFold(g *Graph) (bool, error) {
	changed := false
	for _, n := range g.Nodes() {
		if n.Attrs == nil {
			continue
		}
		if _, ok := n.Attrs["const"]; ok {
			continue
		}
		if len(n.Inputs) == 0 {
			continue
		}
		allConst := true
		var ins []*tensor.Tensor
		for _, eid := range n.Inputs {
			e := g.edge(eid)
			if e == nil {
				allConst = false
				break
			}
			src, err := g.Node(e.From)
			if err != nil {
				return false, err
			}
			c, ok := constOutputs(src)
			if !ok {
				allConst = false
				break
			}
			if e.FromPort >= len(c) {
				allConst = false
				break
			}
			ins = append(ins, c[e.FromPort])
		}
		if !allConst {
			continue
		}
		outs, err := n.Op.Forward(ins)
		if err != nil {
			return false, errors.Wrap(err, errors.CodeInternal, "constant fold failed").
				WithField("node", n.ID).WithField("op", n.Op.Name())
		}
		if n.Attrs == nil {
			n.Attrs = map[string]any{}
		}
		n.Attrs["const"] = outs
		changed = true
	}
	return changed, nil
}

// constOutputs returns the constant outputs of a node.
func constOutputs(n *Node) ([]*tensor.Tensor, bool) {
	if n.Attrs == nil {
		return nil, false
	}
	c, ok := n.Attrs["const"].([]*tensor.Tensor)
	return c, ok && len(c) > 0
}

// deadCodeElimination removes nodes that do not
// transitively feed a sink node and have no side
// effects (side-effecting ops declare "side_effect").
func (o *Optimizer) deadCodeElimination(g *Graph) (bool, error) {
	order, err := g.TopologicalSort()
	if err != nil {
		return false, err
	}
	g.mu.RLock()
	var roots []int
	for id := range g.outputs {
		roots = append(roots, id)
	}
	g.mu.RUnlock()
	needed := map[int]bool{}
	var mark func(id int)
	mark = func(id int) {
		if needed[id] {
			return
		}
		needed[id] = true
		n, err := g.Node(id)
		if err != nil {
			return
		}
		for _, eid := range n.Inputs {
			e := g.edge(eid)
			if e == nil {
				continue
			}
			mark(e.From)
		}
	}
	if len(roots) > 0 {
		for _, id := range roots {
			mark(id)
		}
	} else {
		for _, id := range order {
			n, _ := g.Node(id)
			if len(n.Outputs) == 0 {
				mark(id)
			}
		}
	}
	removed := 0
	for _, id := range order {
		if needed[id] {
			continue
		}
		n, err := g.Node(id)
		if err != nil {
			continue
		}
		if n.Attrs != nil {
			if _, sideEffect := n.Attrs["side_effect"]; sideEffect {
				continue
			}
		}
		if err := removeNode(g, id); err != nil {
			return false, err
		}
		removed++
	}
	o.nodesRemoved += removed
	return removed > 0, nil
}

// removeNode tombstones a node and its edges.
// Node and edge IDs remain stable: tombstoned
// entries are skipped by every accessor.
func removeNode(g *Graph, id int) error {
	g.mu.Lock()
	defer g.mu.Unlock()
	n := g.nodes[id]
	if n == nil || n.removed {
		return nil
	}
	n.removed = true
	for _, eid := range append(append([]int(nil), n.Inputs...), n.Outputs...) {
		if eid < 0 || eid >= len(g.edges) {
			continue
		}
		e := g.edges[eid]
		if e == nil || e.removed {
			continue
		}
		e.removed = true
	}
	return nil
}

// fuseElementwise merges chains of single-input,
// single-output elementwise ops into one fused node.
// The fused node applies the composed functions in
// order; only OpFunc nodes with fuseable markers
// (attribute "fuseable" = true) participate.
func (o *Optimizer) fuseElementwise(g *Graph) (bool, error) {
	order, err := g.TopologicalSort()
	if err != nil {
		return false, err
	}
	fused := 0
	for _, id := range order {
		n, err := g.Node(id)
		if err != nil || n.removed {
			continue
		}
		ins := liveInputs(g, n)
		outs := liveOutputs(g, n)
		if !fuseable(n) || len(ins) != 1 || len(outs) != 1 {
			continue
		}
		e := g.edge(ins[0])
		if e == nil {
			continue
		}
		src, err := g.Node(e.From)
		if err != nil || src.removed {
			continue
		}
		srcIns := liveInputs(g, src)
		if !fuseable(src) || len(liveOutputs(g, src)) != 1 {
			continue
		}
		// Build the composed op: src then n.
		fusedOp := &OpFunc{
			OpName: src.Op.Name() + "+" + n.Op.Name(),
		}
		if sf, ok := src.Op.(OpFunc); ok {
			if nf, ok2 := n.Op.(OpFunc); ok2 {
				fwdA := sf.ForwardFn
				fwdB := nf.ForwardFn
				fusedOp.ShapeFn = sf.ShapeFn
				fusedOp.ForwardFn = func(inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
					mid, err := fwdA(inputs)
					if err != nil {
						return nil, err
					}
					return fwdB(mid)
				}
			}
		}
		if fusedOp.ForwardFn == nil {
			continue
		}
		// Rewire: replace src and n with fusedOp.
		newID, err := g.AddNode(fusedOp, map[string]any{"fused": true})
		if err != nil {
			return false, err
		}
		for _, inEID := range srcIns {
			inEdge := g.edge(inEID)
			if inEdge == nil {
				continue
			}
			if _, err := g.AddEdge(inEdge.From, newID, inEdge.FromPort, 0); err != nil {
				return false, err
			}
		}
		for _, outEID := range outs {
			outEdge := g.edge(outEID)
			if outEdge == nil {
				continue
			}
			if _, err := g.AddEdge(newID, outEdge.To, 0, outEdge.ToPort); err != nil {
				return false, err
			}
		}
		if err := removeNode(g, n.ID); err != nil {
			return false, err
		}
		if err := removeNode(g, src.ID); err != nil {
			return false, err
		}
		fused++
	}
	o.nodesFused += fused
	return fused > 0, nil
}

// liveInputs returns the node's live input edge IDs.
func liveInputs(g *Graph, n *Node) []int {
	out := make([]int, 0, len(n.Inputs))
	for _, eid := range n.Inputs {
		if e := g.edge(eid); e != nil {
			out = append(out, eid)
		}
	}
	return out
}

// liveOutputs returns the node's live output edge IDs.
func liveOutputs(g *Graph, n *Node) []int {
	out := make([]int, 0, len(n.Outputs))
	for _, eid := range n.Outputs {
		if e := g.edge(eid); e != nil {
			out = append(out, eid)
		}
	}
	return out
}

func fuseable(n *Node) bool {
	if n == nil || n.Attrs == nil {
		return false
	}
	v, ok := n.Attrs["fuseable"].(bool)
	return ok && v
}
