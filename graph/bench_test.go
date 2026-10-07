package graph_test

import (
	"context"
	"testing"

	"github.com/astrovox/astrovox/graph"
	"github.com/astrovox/astrovox/tensor"
)

// copyOp returns a pass-through operator.
func copyOp(name string) graph.Op {
	return graph.OpFunc{
		OpName: name,
		ShapeFn: func(inputs []tensor.Shape) ([]tensor.Shape, error) {
			if len(inputs) == 0 {
				s, err := tensor.NewShape(64, 64)
				if err != nil {
					return nil, err
				}
				return []tensor.Shape{s}, nil
			}
			return []tensor.Shape{inputs[0]}, nil
		},
		ForwardFn: func(inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
			if len(inputs) == 0 {
				return nil, nil
			}
			return []*tensor.Tensor{inputs[0]}, nil
		},
	}
}

func benchmarkGraph(b *testing.B, nodes int) *graph.Graph {
	g := graph.New("bench")
	src, err := g.AddNode(copyOp("source"), nil)
	if err != nil {
		b.Fatal(err)
	}
	prev := src
	for i := 1; i < nodes; i++ {
		id, err := g.AddNode(copyOp("op"), nil)
		if err != nil {
			b.Fatal(err)
		}
		if _, err := g.AddEdge(prev, id, 0, 0); err != nil {
			b.Fatal(err)
		}
		prev = id
	}
	if err := g.MarkOutput(prev); err != nil {
		b.Fatal(err)
	}
	return g
}

func BenchmarkGraphAddNode(b *testing.B) {
	g := graph.New("bench")
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := g.AddNode(copyOp("op"), nil); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkGraphAddEdge(b *testing.B) {
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		g := graph.New("inner")
		x, _ := g.AddNode(copyOp("x"), nil)
		y, _ := g.AddNode(copyOp("y"), nil)
		if _, err := g.AddEdge(x, y, 0, 0); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkGraphTopologicalSort(b *testing.B) {
	g := benchmarkGraph(b, 1000)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := g.TopologicalSort(); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkExecutorRun(b *testing.B) {
	g := benchmarkGraph(b, 100)
	exec, err := graph.NewExecutor(g)
	if err != nil {
		b.Fatal(err)
	}
	input, err := tensor.Ones(tensor.Float32, []int{64, 64})
	if err != nil {
		b.Fatal(err)
	}
	ctx := context.Background()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := exec.Run(ctx, []*tensor.Tensor{input}); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkGraphValidate(b *testing.B) {
	g := benchmarkGraph(b, 1000)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if err := g.Validate(); err != nil {
			b.Fatal(err)
		}
	}
}
