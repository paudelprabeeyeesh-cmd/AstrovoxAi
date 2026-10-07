package backend

import (
	"math"
	"testing"
)

func TestCPUBackendMatMul(t *testing.T) {
	b := NewCPUBackend()
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8}
	out, err := b.MatMul(a, bb, 2, 2, 2)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{19, 22, 43, 50}
	for i := range expected {
		if math.Abs(out[i]-expected[i]) > 1e-9 {
			t.Errorf("MatMul[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestCPUBackendAdd(t *testing.T) {
	b := NewCPUBackend()
	a := []float64{1, 2, 3}
	bb := []float64{4, 5, 6}
	out, err := b.Add(a, bb)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{5, 7, 9}
	for i := range expected {
		if out[i] != expected[i] {
			t.Errorf("Add[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestCPUBackendRelu(t *testing.T) {
	b := NewCPUBackend()
	x := []float64{-1, 0, 1}
	out := b.Relu(x)
	if out[0] != 0 || out[1] != 0 || out[2] != 1 {
		t.Errorf("Relu unexpected: %v", out)
	}
}

func TestCPUBackendSoftmax(t *testing.T) {
	b := NewCPUBackend()
	x := []float64{1, 2, 3}
	out, err := b.Softmax(x, 1)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var sum float64
	for _, v := range out {
		sum += v
	}
	if math.Abs(sum-1.0) > 1e-9 {
		t.Errorf("Softmax sum = %v, want 1.0", sum)
	}
}

func TestCPUBackendName(t *testing.T) {
	b := NewCPUBackend()
	if b.Name() != "cpu" {
		t.Errorf("Name = %s, want cpu", b.Name())
	}
}

func TestCPUBackendSupportedDtypes(t *testing.T) {
	b := NewCPUBackend()
	dtypes := b.SupportedDtypes()
	if len(dtypes) == 0 {
		t.Fatal("expected supported dtypes")
	}
}
