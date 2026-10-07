package integration_test

import (
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/ir"
)

func TestIntegrationIRGraphvizWithNodes(t *testing.T) {
	g := ir.NewGraph()
	g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "const"})
	g.AddNode(&ir.Node{Kind: ir.NodeKindVariable, Op: "var", Inputs: []int64{1}})
	var buf bytes.Buffer
	if err := g.WriteGraphviz(&buf); err != nil {
		t.Fatalf("graphviz write failed: %v", err)
	}
	if !bytes.Contains(buf.Bytes(), []byte("const")) {
		t.Fatal("expected const in graphviz output")
	}
}

func TestIntegrationBackendCPUThreadPool(t *testing.T) {
	pool := backend.NewCPUThreadPool(2)
	defer pool.Shutdown()
	var wg sync.WaitGroup
	wg.Add(1)
	pool.Submit(func() { wg.Done() })
	wg.Wait()
}

func TestIntegrationIRShapeString(t *testing.T) {
	var s ir.Shape
	if s.String() != "[]" {
		t.Fatalf("expected []")
	}
	if ir.Shape{2, 3}.String() != "[2x3]" {
		t.Fatalf("expected [2x3]")
	}
}

func TestIntegrationBackendColumnMajorLayout(t *testing.T) {
	layout := backend.NewColumnMajor([]int{2, 3})
	if layout.Layout != backend.ColumnMajorLayout {
		t.Fatalf("expected column major")
	}
	if len(layout.Strides) != 2 {
		t.Fatalf("expected 2 strides")
	}
}

func TestIntegrationIRDataTypes(t *testing.T) {
	types := []ir.DataType{ir.DataTypeFloat32, ir.DataTypeFloat64, ir.DataTypeInt32, ir.DataTypeInt64, ir.DataTypeBool}
	for _, dt := range types {
		n := &ir.Node{Kind: ir.NodeKindConstant, Op: "c", DType: dt}
		if n.DType != dt {
			t.Fatalf("expected dtype %s", dt)
		}
	}
}

func TestIntegrationOptimizerOperatorFusion(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "add", []string{"a"})
	g.AddNode("c", "add", []string{"b"})
	g.Output = "c"
	g.OperatorFusion()
}

func TestIntegrationBackendSchedulerBackendAddAsync(t *testing.T) {
	b := backend.NewCPUBackend()
	sb := backend.NewSchedulerBackend(b, 2)
	defer sb.Close()
	out, err := sb.AddAsync([]float64{1, 2, 3}, []float64{4, 5, 6})
	if err != nil {
		t.Fatalf("add async failed: %v", err)
	}
	if out[0] != 5 || out[1] != 7 || out[2] != 9 {
		t.Errorf("unexpected result: %v", out)
	}
}

func TestIntegrationIRNodeCloneDeepCopy(t *testing.T) {
	g := ir.NewGraph()
	id := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c", Shape: ir.Shape{2}, DType: ir.DataTypeFloat32, Attrs: map[string]interface{}{"value": []float64{1.0, 2.0}}, Metadata: map[string]string{"key": "val"}})
	n := g.GetNode(id).Clone()
	if n == nil {
		t.Fatal("expected cloned node")
	}
	if n.ID != id {
		t.Fatalf("expected id %d, got %d", id, n.ID)
	}
	if n.Metadata["key"] != "val" {
		t.Fatalf("expected metadata preserved")
	}
}

func TestIntegrationOptimizerTopologicalSortChain(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c", "add", []string{"a", "b"})
	order := g.TopologicalSort()
	if len(order) != 3 {
		t.Fatalf("expected 3 nodes, got %d", len(order)))
	}
}

func TestIntegrationBackendDefaultBackend(t *testing.T) {
	backend.RegisterBackend("cpu", backend.NewCPUBackend())
	b := backend.DefaultBackend()
	if b == nil || b.Name() != "cpu" {
		t.Fatal("expected default cpu backend")
	}
}

func TestIntegrationIRInferType(t *testing.T) {
	g := ir.NewGraph()
	id := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "c", Attrs: map[string]interface{}{"value": 3.14}})
	if err := g.InferType(); err != nil {
		t.Fatalf("infer type failed: %v", err)
	}
	if g.Nodes[id].DType != ir.DataTypeFloat64 {
		t.Fatalf("expected float64, got %s", g.Nodes[id].DType)
	}
}

func TestIntegrationOptimizerInlineConstants(t *testing.T) {
	g := optimizer.NewGraph()
	g.Constants["a"] = 2.0
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "add", []string{"a"})
	g.Output = "b"
	g.InlineConstants()
}

func TestIntegrationBackendMemoryLayoutStride(t *testing.T) {
	layout := backend.NewRowMajor([]int{2, 3})
	if layout.Strides[0] != 3 || layout.Strides[1] != 1 {
		t.Errorf("unexpected strides: %v", layout.Strides)
	}
}

func TestIntegrationIRBuilderMultipleOutputs(t *testing.T) {
	b := ir.NewGraphBuilder()
	a := b.Constant("a", 1.0, ir.Shape{}, ir.DataTypeFloat64)
	b2 := b.Constant("b", 2.0, ir.Shape{}, ir.DataTypeFloat64)
	b.SetOutput(a, b2)
	g := b.Build()
	if len(g.Output) != 2 {
		t.Fatalf("expected 2 outputs, got %d", len(g.Output))
	}
}

func TestIntegrationOptimizerCommonSubexpressionElimination(t *testing.T) {
	g := optimizer.NewGraph()
	g.AddNode("a", "constant", nil)
	g.AddNode("b", "constant", nil)
	g.AddNode("c1", "add", []string{"a", "b"})
	g.AddNode("c2", "add", []string{"a", "b"})
	g.Output = "c1"
	g.CommonSubexpressionElimination()
}

func TestIntegrationBackendVecMatMulWithPool(t *testing.T) {
	out, err := backend.VecMatMul([]float64{1, 2, 3, 4}, []float64{5, 6, 7, 8}, 2, 2, 2, backend.NewCPUThreadPool(2))
	if err != nil {
		t.Fatalf("vec matmul failed: %v", err)
	}
	if len(out) != 4 {
		t.Fatalf("expected 4 outputs, got %d", len(out))
	}
}

func TestIntegrationIRValidateGraph(t *testing.T) {
	g := ir.NewGraph()
	if err := g.ValidateGraph(); err != nil {
		t.Fatalf("empty graph should validate: %v", err)
	}
}

func TestIntegrationRuntimeWaitMultiple(t *testing.T) {
	s := runtime.NewScheduler(2)
	defer s.Stop()
	f1 := s.Submit(func() error { return nil })
	f2 := s.Submit(func() error { return nil })
	if err := s.Wait(f1, f2); err != nil {
		t.Fatalf("wait failed: %v", err)
	}
}
