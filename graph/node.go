// Package graph implements the Astrovox computational
// graph: nodes, edges, builders, topological sorting,
// cycle detection, execution, optimization, and
// GraphViz visualization.
package graph

import (
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Op is the interface every graph node operator implements.
type Op interface {
	// Name returns the operator identifier.
	Name() string
	// InferShape computes output shapes from input shapes.
	InferShape(inputs []tensor.Shape) ([]tensor.Shape, error)
	// Forward computes outputs from inputs.
	Forward(inputs []*tensor.Tensor) ([]*tensor.Tensor, error)
}

// OpFunc adapts a function to the Op interface.
type OpFunc struct {
	OpName     string
	ShapeFn    func(inputs []tensor.Shape) ([]tensor.Shape, error)
	ForwardFn  func(inputs []*tensor.Tensor) ([]*tensor.Tensor, error)
}

// Name implements Op.
func (f OpFunc) Name() string { return f.OpName }

// InferShape implements Op.
func (f OpFunc) InferShape(inputs []tensor.Shape) ([]tensor.Shape, error) {
	if f.ShapeFn == nil {
		return nil, errors.New(errors.CodeUnimplemented, "shape inference not provided").
			WithField("op", f.OpName)
	}
	return f.ShapeFn(inputs)
}

// Forward implements Op.
func (f OpFunc) Forward(inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
	if f.ForwardFn == nil {
		return nil, errors.New(errors.CodeUnimplemented, "forward not provided").
			WithField("op", f.OpName)
	}
	return f.ForwardFn(inputs)
}

// Node is a graph vertex wrapping an operator.
type Node struct {
	ID    int
	Op    Op
	Attrs map[string]any
	// Inputs are edge indices into the graph edge table.
	Inputs []int
	// Outputs are edge indices into the graph edge table.
	Outputs []int
	// removed marks nodes deleted by optimization;
	// tombstoned nodes are skipped by all accessors.
	removed bool
	// Cached inference results.
	outShapes []tensor.Shape
	visited   bool
}

// OutShapes returns the last inferred output shapes.
func (n *Node) OutShapes() []tensor.Shape { return n.outShapes }

// Edge is a directed data dependency between nodes.
type Edge struct {
	ID       int
	From     int // source node ID
	To       int // destination node ID
	FromPort int // output port on source
	ToPort   int // input port on destination
	// removed marks edges deleted by optimization;
	// tombstoned edges are skipped by all accessors.
	removed bool
}

// Endpoints returns the (node, port) pair of the edge tail.
func (e *Edge) Endpoints() (int, int) { return e.From, e.FromPort }

// Target returns the (node, port) pair of the edge head.
func (e *Edge) Target() (int, int) { return e.To, e.ToPort }
