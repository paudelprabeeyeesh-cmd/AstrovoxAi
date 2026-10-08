package graph_test

import (
	"context"
	"testing"

	"github.com/astrovox/astrovox/graph"
	"github.com/astrovox/astrovox/tensor"
)

// stressOp is a minimal pass-through operator for
// building large graphs cheaply.
type stressOp struct{}

func (stressOp) Name() string { return "stress" }
func (stressOp) InferShape(inputs []tensor.Shape) ([]tensor.Shape, error) {
	if len(inputs) == 0 {
		s, err := tensor.NewShape(1)
		if err != nil {
			return nil, err
		}
		return []tensor.Shape{s}, nil
	}
	return []tensor.Shape{inputs[0]}, nil
}
func (stressOp) Forward(inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
	if len(inputs) == 0 {
		return nil, nil
	}
	return []*tensor.Tensor{inputs[0]}, nil
}

func buildChain(tb testing.TB, nodes int) *graph.Graph {
	g := graph.New("stress")
	prev, err := g.AddNode(stressOp{}, nil)
	if err != nil {
		tb.Fatal(err)
	}
	for i := 1; i < nodes; i++ {
		id, err := g.AddNode(stressOp{}, nil)
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

// TestStress_DeepGraphTopologicalSort sorts a 100k-node
// chain within a bounded time.
func TestStress_DeepGraphTopologicalSort(t *testing.T) {
	g := buildChain(t, 100_000)
	order, err := g.TopologicalSort()
	if err != nil {
		t.Fatal(err)
	}
	if len(order) != 100_000 {
		t.Fatalf("order length = %d, want 100000", len(order))
	}
	for i, id := range order {
		if id != i {
			t.Fatalf("order[%d] = %d, chain must be sequential", i, id)
		}
	}
}

// TestStress_DeepGraphValidate validates a 100k-node chain.
func TestStress_DeepGraphValidate(t *testing.T) {
	g := buildChain(t, 100_000)
	if err := g.Validate(); err != nil {
		t.Fatal(err)
	}
}

// TestStress_WideGraph builds a fan-out graph: one
// source with 10k consumers.
func TestStress_WideGraph(t *testing.T) {
	g := graph.New("wide")
	src, err := g.AddNode(stressOp{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	last := src
	for i := 0; i < 10_000; i++ {
		id, err := g.AddNode(stressOp{}, nil)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := g.AddEdge(src, id, 0, 0); err != nil {
			t.Fatal(err)
		}
		last = id
	}
	if err := g.MarkOutput(last); err != nil {
		t.Fatal(err)
	}
	order, err := g.TopologicalSort()
	if err != nil {
		t.Fatal(err)
	}
	if len(order) != 10_001 {
		t.Fatalf("order length = %d, want 10001", len(order))
	}
}

// TestStress_DiamondGraph builds 10k diamonds
// (source → a,b → sink per diamond).
func TestStress_DiamondGraph(t *testing.T) {
	g := graph.New("diamond")
	src, err := g.AddNode(stressOp{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	prev := src
	for i := 0; i < 10_000; i++ {
		a, err := g.AddNode(stressOp{}, nil)
		if err != nil {
			t.Fatal(err)
		}
		b, err := g.AddNode(stressOp{}, nil)
		if err != nil {
			t.Fatal(err)
		}
		sink, err := g.AddNode(stressOp{}, nil)
		if err != nil {
			t.Fatal(err)
		}
		for j, mid := range []int{a, b} {
			if _, err := g.AddEdge(prev, mid, 0, 0); err != nil {
				t.Fatal(err)
			}
			if _, err := g.AddEdge(mid, sink, 0, j); err != nil {
				t.Fatal(err)
			}
		}
		prev = sink
	}
	if err := g.MarkOutput(prev); err != nil {
		t.Fatal(err)
	}
	order, err := g.TopologicalSort()
	if err != nil {
		t.Fatal(err)
	}
	want := 1 + 3*10_000
	if len(order) != want {
		t.Fatalf("order length = %d, want %d", len(order), want)
	}
	if err := g.Validate(); err != nil {
		t.Fatal(err)
	}
}

// TestStress_ExecutorDeepChain executes a 1k-node chain.
func TestStress_ExecutorDeepChain(t *testing.T) {
	g := buildChain(t, 1_000)
	exec, err := graph.NewExecutor(g)
	if err != nil {
		t.Fatal(err)
	}
	input, err := tensor.Ones(tensor.Float32, []int{1})
	if err != nil {
		t.Fatal(err)
	}
	outs, err := exec.Run(context.Background(), []*tensor.Tensor{input})
	if err != nil {
		t.Fatal(err)
	}
	if len(outs) == 0 {
		t.Fatal("executor returned no outputs")
	}
}

// TestStress_OptimizerLargeGraph runs the
// optimizer's dead-code elimination over a 20k-node
// graph with a dead tail.
func TestStress_OptimizerLargeGraph(t *testing.T) {
	g := graph.New("dce-stress")
	src, err := g.AddNode(stressOp{}, nil)
	if err != nil {
		t.Fatal(err)
	}
	prev := src
	for i := 1; i < 20_000; i++ {
		id, err := g.AddNode(stressOp{}, nil)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := g.AddEdge(prev, id, 0, 0); err != nil {
			t.Fatal(err)
		}
		prev = id
	}
	// The chain tail is unmarked: with no output
	// reachable from it, DCE may remove the tail.
	opt := graph.NewOptimizer()
	if err := opt.Optimize(g); err != nil {
		t.Fatal(err)
	}
	if g.NodeCount() < 1 {
		t.Fatal("optimizer removed the entire graph")
	}
}
