package integration_test

import (
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/ir"
	"github.com/astrovox/astrovox/internal/optimizer"
)

func TestIntegrationBackendSoftmaxSum(t *testing.T) {
	b := backend.NewCPUBackend()
	out, err := b.Softmax([]float64{1, 2, 3}, 1)
	if err != nil {
		t.Fatalf("softmax failed: %v", err)
	}
	var sum float64
	for _, v := range out {
		sum += v
	}
	if sum != 1.0 {
		t.Errorf("softmax sum = %f, want 1.0", sum)
	}
}

func TestIntegrationIRShapeInference(t *testing.T) {
	g := ir.NewGraph()
	g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c", Shape: ir.Shape{2, 3}, DType: ir.DataTypeFloat32})
	if err := g.InferShape(); err != nil {
		t.Fatalf("infer shape failed: %v", err)
	}
}

func TestIntegrationOptimizerMultiplePasses(t *testing.T) {
	g := optimizer.NewGraph()
	g.Constants["a"] = 2.0
	g.Constants["b"] = 3.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	g.Output = "c"
	g.ConstantFolding()
	g.DeadCodeElimination()
	n := g.Nodes["c"]
	if !n.Computed || n.Value != 5.0 {
		t.Fatalf("expected folded value, got %v", n.Value)
	}
}

func TestIntegrationBackendDeviceString(t *testing.T) {
	if backend.DeviceCPU.String() != "cpu" {
		t.Errorf("expected cpu, got %s", backend.DeviceCPU.String())
	}
}

func TestIntegrationBackendMemoryLayout(t *testing.T) {
	layout := backend.NewRowMajor([]int{2, 3})
	if layout.Layout != backend.RowMajorLayout {
		t.Fatalf("expected row major")
	}
	if len(layout.Strides) != 2 {
		t.Fatalf("expected 2 strides")
	}
}

func TestIntegrationIRNodeClone(t *testing.T) {
	g := ir.NewGraph()
	id := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c", Shape: ir.Shape{2}, DType: ir.DataTypeFloat32})
	n := g.GetNode(id).Clone()
	if n == nil {
		t.Fatal("expected cloned node")
	}
	if n.ID != id {
		t.Fatalf("expected same id, got %d", n.ID)
	}
}

func TestIntegrationOptimizerGraphValidation(t *testing.T) {
	g := optimizer.NewGraph()
	if g.Output != "" {
		t.Fatal("expected empty output")
	}
}

func TestIntegrationBackendVecMatMul(t *testing.T) {
	out, err := backend.VecMatMul([]float64{1, 2, 3, 4}, []float64{5, 6, 7, 8}, 2, 2, 2, nil)
	if err != nil {
		t.Fatalf("vec matmul failed: %v", err)
	}
	if len(out) != 4 {
		t.Fatalf("expected 4 outputs, got %d", len(out))
	}
}

func TestIntegrationIRMetadataEnrichment(t *testing.T) {
	g := ir.NewGraph()
	id := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c", Shape: ir.Shape{2, 3}, DType: ir.DataTypeFloat32})
	g.EnrichMetadata()
	n := g.GetNode(id)
	if n.Metadata["kind"] != "constant" {
		t.Fatalf("expected kind metadata")
	}
}

func TestIntegrationBackendSchedulerBackend(t *testing.T) {
	b := backend.NewCPUBackend()
	sb := backend.NewSchedulerBackend(b, 2)
	defer sb.Close()
	out, err := sb.MatMulAsync([]float64{1, 2, 3, 4}, []float64{5, 6, 7, 8}, 2, 2, 2)
	if err != nil {
		t.Fatalf("matmul async failed: %v", err)
	}
	if len(out) != 4 {
		t.Fatalf("expected 4 outputs, got %d", len(out))
	}
}

func TestIntegrationRuntimeTracerSpans(t *testing.T) {
	tr := runtime.NewTracer()
	s1 := tr.Start("span1")
	s1.End(10)
	spans := tr.SpansList()
	if len(spans) != 1 {
		t.Fatalf("expected 1 span, got %d", len(spans))
	}
}

func TestIntegrationIRBuilder(t *testing.T) {
	b := ir.NewGraphBuilder()
	a := b.Constant("a", 1.0, ir.Shape{}, ir.DataTypeFloat64)
	b2 := b.Constant("b", 2.0, ir.Shape{}, ir.DataTypeFloat64)
	c := b.Call("add", []int64{a, b2}, ir.Shape{}, ir.DataTypeFloat64)
	b.SetOutput(c)
	g := b.Build()
	if g.NodeCount() != 3 {
		t.Fatalf("expected 3 nodes, got %d", g.NodeCount())
	}
}

func TestIntegrationBackendCPUBackendName(t *testing.T) {
	b := backend.NewCPUBackend()
	if b.Name() != "cpu" {
		t.Errorf("Name = %s, want cpu", b.Name())
	}
}

func TestIntegrationOptimizerCommonSubexpression(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c1", "add", []string{"a", "b"})
	g.AddNode("c2", "add", []string{"a", "b"})
	g.Output = "c1"
	g.CommonSubexpressionElimination()
	if len(g.Nodes) > 3 {
		t.Fatalf("expected CSE to reduce nodes, got %d", len(g.Nodes))
	}
}

func TestIntegrationRuntimeProfilerMetrics(t *testing.T) {
	p := runtime.NewProfiler()
	p.Time("op1", func() {})
	p.Time("op2", func() {})
	metrics := p.Metrics()
	if len(metrics) != 2 {
		t.Fatalf("expected 2 metrics, got %d", len(metrics))
	}
}

func TestIntegrationIRCycleDetection(t *testing.T) {
	g := ir.NewGraph()
	id1 := g.AddNode(&ir.Node{Kind: ir.NodeKindCall, Op: "a"})
	id2 := g.AddNode(&ir.Node{Kind: ir.NodeKindCall, Op: "b", Inputs: []int64{id1}})
	g.Nodes[id1].Inputs = []int64{id2}
	if err := g.ValidateGraph(); err == nil {
		t.Fatal("expected cycle detection error")
	}
}

func TestIntegrationBackendAddShapeMismatch(t *testing.T) {
	b := backend.NewCPUBackend()
	_, err := b.Add([]float64{1, 2}, []float64{1})
	if err == nil {
		t.Fatal("expected shape mismatch error")
	}
}

func TestIntegrationIRTopologicalSortChain(t *testing.T) {
	g := ir.NewGraph()
	id1 := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "a"})
	id2 := g.AddNode(&ir.Node{Kind: ir.NodeKindCall, Op: "b", Inputs: []int64{id1}})
	id3 := g.AddNode(&ir.Node{Kind: ir.NodeKindCall, Op: "c", Inputs: []int64{id2}})
	order := g.TopologicalSort()
	if order[0].ID != id1 || order[1].ID != id2 || order[2].ID != id3 {
		t.Fatal("unexpected topological order")
	}
}

func TestIntegrationOptimizerDCEEmptyOutput(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.Output = ""
	g.DeadCodeElimination()
	if len(g.Nodes) != 0 {
		t.Fatalf("expected 0 nodes, got %d", len(g.Nodes))
	}
}

func TestIntegrationBackendMatMulInvalidDims(t *testing.T) {
	b := backend.NewCPUBackend()
	_, err := b.MatMul([]float64{1, 2}, []float64{1}, 2, 2, 2)
	if err == nil {
		t.Fatal("expected invalid dims error")
	}
}

func TestIntegrationRuntimeSchedulerWaitError(t *testing.T) {
	s := runtime.NewScheduler(1)
	defer s.Stop()
	expectedErr := runtime.ErrCancelled
	f := s.Submit(func() error { return expectedErr })
	if err := f.Wait(); err != expectedErr {
		t.Fatalf("expected ErrCancelled, got %v", err)
	}
}
