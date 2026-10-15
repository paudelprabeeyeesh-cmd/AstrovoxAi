package runtime_test

import (
	"context"
	"testing"

	"github.com/astrovox/astrovox/graph"
	"github.com/astrovox/astrovox/runtime"
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

func graphChain(tb testing.TB, nodes int) *graph.Graph {
	g := graph.New("bench")
	src, err := g.AddNode(copyOp("source"), nil)
	if err != nil {
		tb.Fatal(err)
	}
	prev := src
	for i := 1; i < nodes; i++ {
		id, err := g.AddNode(copyOp("op"), nil)
		if err != nil {
			tb.Fatal(err)
		}
		if _, err := g.AddEdge(prev, id, 0, 0); err != nil {
			tb.Fatal(err)
		}
		prev = id
	}
	if err := g.MarkOutput(prev); err != nil {
		tb.Fatal(err)
	}
	return g
}

func benchTask() runtime.Task {
	return func(ctx context.Context) ([]*tensor.Tensor, error) {
		t, err := tensor.Zeros(tensor.Float32, []int{16, 16})
		if err != nil {
			return nil, err
		}
		return []*tensor.Tensor{t}, nil
	}
}

func BenchmarkEngineSubmit(b *testing.B) {
	e := runtime.NewEngine(4)
	ctx := context.Background()
	task := benchTask()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		f, err := e.Submit(ctx, task)
		if err != nil {
			b.Fatal(err)
		}
		if _, err := f.Wait(); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkEngineSubmitParallel(b *testing.B) {
	e := runtime.NewEngine(4)
	ctx := context.Background()
	task := benchTask()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		const workers = 8
		futures := make([]runtime.Future, workers)
		for j := range futures {
			f, err := e.Submit(ctx, task)
			if err != nil {
				b.Fatal(err)
			}
			futures[j] = f
		}
		for _, f := range futures {
			if _, err := f.Wait(); err != nil {
				b.Fatal(err)
			}
		}
	}
}

func BenchmarkSessionRun(b *testing.B) {
	g := graphChain(b, 20)
	s, err := runtime.NewSession(g)
	if err != nil {
		b.Fatal(err)
	}
	input, err := tensor.Ones(tensor.Float32, []int{32, 32})
	if err != nil {
		b.Fatal(err)
	}
	ctx := context.Background()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := s.Run(ctx, []*tensor.Tensor{input}); err != nil {
			b.Fatal(err)
		}
	}
}
