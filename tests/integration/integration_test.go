package integration_test

import (
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/internal/ir"
	"github.com/astrovox/astrovox/internal/optimizer"
	"github.com/astrovox/astrovox/internal/runtime"
)

func TestIntegrationIRAndOptimizer(t *testing.T) {
	g := ir.NewGraph()
	// Use the returned IDs rather than literals: node IDs come from a
	// package-global counter, so hardcoded values break when tests run
	// more than once in the same process (-count=2).
	constant := g.AddNode(&ir.Node{Kind: ir.NodeKindConstant, Op: "a", Shape: ir.Shape{2, 3}, DType: ir.DataTypeFloat32})
	sink := g.AddNode(&ir.Node{Kind: ir.NodeKindCall, Op: "add", Inputs: []int64{constant}, Shape: ir.Shape{2, 3}, DType: ir.DataTypeFloat32})
	g.Output = []int64{sink}
	if err := g.ValidateGraph(); err != nil {
		t.Fatalf("invalid graph: %v", err)
	}
	_ = optimizer.NewGraph()
}

func TestIntegrationBackendAndRuntime(t *testing.T) {
	b := backend.NewCPUBackend()
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8}
	out, err := b.MatMul(a, bb, 2, 2, 2)
	if err != nil {
		t.Fatalf("matmul failed: %v", err)
	}
	if len(out) != 4 {
		t.Fatalf("expected 4 outputs, got %d", len(out))
	}
	s := runtime.NewScheduler(1)
	defer s.Stop()
	f, err := s.Submit(func() error { return nil })
	if err != nil {
		t.Fatalf("submit: %v", err)
	}
	if err := f.Wait(); err != nil {
		t.Fatalf("future failed: %v", err)
	}
}

func TestIntegrationMemoryPool(t *testing.T) {
	_ = backend.NewCPUBackend()
}
