package graph

import (
	"context"
	"sort"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Executor runs a validated graph over concrete tensor
// inputs, executing nodes in topological order.
type Executor struct {
	g *Graph
	// Profiler spans are recorded when profiler is set.
	profiler SpanRecorder
}

// SpanRecorder receives execution spans.
type SpanRecorder interface {
	Start(name string) func()
}

// NewExecutor creates an executor for the graph.
func NewExecutor(g *Graph) (*Executor, error) {
	if g == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil graph")
	}
	if err := g.Validate(); err != nil {
		return nil, err
	}
	return &Executor{g: g}, nil
}

// SetProfiler installs a span recorder.
func (e *Executor) SetProfiler(r SpanRecorder) { e.profiler = r }

// Run executes the graph with the given input tensors
// bound to the graph's source nodes (nodes with no
// inputs). Returns the tensors produced by sink nodes
// (nodes with no outputs) in node-ID order.
func (e *Executor) Run(ctx context.Context, inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
	order, err := e.g.TopologicalSort()
	if err != nil {
		return nil, err
	}
	sources := 0
	for _, id := range order {
		n, _ := e.g.Node(id)
		if len(n.Inputs) == 0 {
			sources++
		}
	}
	if len(inputs) != sources {
		return nil, errors.New(errors.CodeInvalidArgument, "input count mismatch").
			WithField("got", len(inputs)).WithField("want", sources)
	}
	outputs := map[int][]*tensor.Tensor{}
	inputIdx := 0
	for _, id := range order {
		select {
		case <-ctx.Done():
			return nil, errors.Wrap(ctx.Err(), errors.CodeCancelled, "execution cancelled")
		default:
		}
		n, _ := e.g.Node(id)
		if len(n.Inputs) == 0 {
			outputs[id] = []*tensor.Tensor{inputs[inputIdx]}
			inputIdx++
			continue
		}
		ins := make([]*tensor.Tensor, 0, len(n.Inputs))
		for _, eid := range n.Inputs {
			edge := e.g.edge(eid)
			if edge == nil {
				continue
			}
			src := outputs[edge.From]
			if edge.FromPort >= len(src) {
				return nil, errors.New(errors.CodeInvalidArgument, "missing source output").
					WithField("edge", eid).WithField("port", edge.FromPort)
			}
			ins = append(ins, src[edge.FromPort])
		}
		var stop func()
		if e.profiler != nil {
			stop = e.profiler.Start(n.Op.Name())
		}
		outs, err := n.Op.Forward(ins)
		if stop != nil {
			stop()
		}
		if err != nil {
			return nil, errors.Wrap(err, errors.CodeInternal, "node execution failed").
				WithField("node", n.ID).WithField("op", n.Op.Name())
		}
		outputs[id] = outs
	}
	// Sinks are designated outputs when present,
	// otherwise every consumer-less node.
	sinkIDs := e.sinkIDs(order)
	var sinks []*tensor.Tensor
	for _, id := range sinkIDs {
		sinks = append(sinks, outputs[id]...)
	}
	return sinks, nil
}

// sinkIDs returns the graph's sink node IDs in
// topological order.
func (e *Executor) sinkIDs(order []int) []int {
	e.g.mu.RLock()
	var designated []int
	for id := range e.g.outputs {
		designated = append(designated, id)
	}
	e.g.mu.RUnlock()
	if len(designated) > 0 {
		sort.Ints(designated)
		return designated
	}
	var sinks []int
	for _, id := range order {
		n, _ := e.g.Node(id)
		if len(n.Outputs) == 0 {
			sinks = append(sinks, id)
		}
	}
	return sinks
}

// InferOutputs returns the statically inferred output
// shapes of the sink nodes.
func (e *Executor) InferOutputs() ([]tensor.Shape, error) {
	if err := e.g.Validate(); err != nil {
		return nil, err
	}
	order, err := e.g.TopologicalSort()
	if err != nil {
		return nil, err
	}
	var sinks []tensor.Shape
	for _, id := range e.sinkIDs(order) {
		n, err := e.g.Node(id)
		if err != nil {
			return nil, err
		}
		sinks = append(sinks, n.OutShapes()...)
	}
	return sinks, nil
}
