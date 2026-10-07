package integration_test

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/ir"
	"github.com/astrovox/astrovox/internal/optimizer"
	"github.com/astrovox/astrovox/internal/runtime"
)

func TestIntegrationBackendMatMulAccuracy(t *testing.T) {
	b := backend.NewCPUBackend()
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8}
	out, err := b.MatMul(a, bb, 2, 2, 2)
	if err != nil {
		t.Fatalf("matmul failed: %v", err)
	}
	expected := []float64{19, 22, 43, 50}
	for i := range expected {
		if math.Abs(out[i]-expected[i]) > 1e-9 {
			t.Errorf("MatMul[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestIntegrationRuntimeSubmitMany(t *testing.T) {
	s := runtime.NewScheduler(2)
	defer s.Stop()
	tasks := []runtime.Task{
		func() error { return nil },
		func() error { return nil },
	}
	futures := s.SubmitMany(tasks)
	if len(futures) != 2 {
		t.Fatalf("expected 2 futures, got %d", len(futures))
	}
}

func TestIntegrationIRUnmarshalRoundTrip(t *testing.T) {
	g := ir.NewGraph()
	g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c"})
	b, err := g.MarshalJSON()
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	g2 := ir.NewGraph()
	if err := g2.UnmarshalJSON(b); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if g2.NodeCount() != 1 {
		t.Fatalf("expected 1 node, got %d", g2.NodeCount())
	}
}

func TestIntegrationOptimizerInlineConstants(t *testing.T) {
	g := optimizer.NewGraph()
	g.Constants["a"] = 2.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "add", []string{"a"})
	g.Output = "b"
	g.InlineConstants()
	if len(g.Constants) != 0 {
		t.Fatalf("expected constants inlined")
	}
}

func TestIntegrationBackendThreadPool(t *testing.T) {
	b := backend.NewCPUBackend()
	sb := backend.NewSchedulerBackend(b, 2)
	defer sb.Close()
	out, err := sb.AddAsync([]float64{1, 2}, []float64{3, 4})
	if err != nil {
		t.Fatalf("add async failed: %v", err)
	}
	if out[0] != 4 || out[1] != 6 {
		t.Errorf("unexpected result: %v", out)
	}
}

func TestIntegrationRuntimeProfiler(t *testing.T) {
	p := runtime.NewProfiler()
	p.Time("op", func() {})
	metrics := p.Metrics()
	if _, ok := metrics["op"]; !ok {
		t.Fatal("expected op metric")
	}
}

func TestIntegrationIRTensorTypes(t *testing.T) {
	types := []ir.DataType{ir.DataTypeFloat32, ir.DataTypeFloat64, ir.DataTypeInt32, ir.DataTypeInt64, ir.DataTypeBool}
	for _, dt := range types {
		n := &ir.Node{Kind: ir.NodeKindConstant, Op: "c", DType: dt}
		if n.DType != dt {
			t.Fatalf("expected dtype %s", dt)
		}
	}
}

func TestIntegrationOptimizerMemoryReuse(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "add", []string{"a"})
	g.AddNode("c", "add", []string{"a"})
	g.Output = "b"
	g.DeadCodeElimination()
	if len(g.Nodes) != 2 {
		t.Fatalf("expected 2 nodes after DCE, got %d", len(g.Nodes))
	}
}

func TestIntegrationBackendVecAdd(t *testing.T) {
	out, err := backend.VecAdd([]float64{1, 2}, []float64{3, 4}, nil)
	if err != nil {
		t.Fatalf("vec add failed: %v", err)
	}
	if out[0] != 4 || out[1] != 6 {
		t.Errorf("unexpected result: %v", out)
	}
}

func TestIntegrationRuntimeFutureDone(t *testing.T) {
	s := runtime.NewScheduler(1)
	defer s.Stop()
	f := s.Submit(func() error { return nil })
	f.Wait()
	if !f.Done() {
		t.Fatal("expected future done")
	}
}
