package backend

import (
	"math"
	"testing"
)

func TestCPUBackendMatMulInvalidDimensions(t *testing.T) {
	b := NewCPUBackend()
	a := []float64{1, 2, 3}
	bb := []float64{4, 5}
	_, err := b.MatMul(a, bb, 2, 2, 2)
	if err == nil {
		t.Fatal("expected error for invalid dimensions")
	}
}

func TestCPUBackendAddShapeMismatch(t *testing.T) {
	b := NewCPUBackend()
	a := []float64{1, 2, 3}
	bb := []float64{4, 5}
	_, err := b.Add(a, bb)
	if err == nil {
		t.Fatal("expected error for shape mismatch")
	}
}

func TestCPUBackendSoftmaxUnsupportedDim(t *testing.T) {
	b := NewCPUBackend()
	x := []float64{1, 2, 3}
	_, err := b.Softmax(x, 0)
	if err == nil {
		t.Fatal("expected error for unsupported dim")
	}
}

func TestCPUBackendSoftmaxEmpty(t *testing.T) {
	b := NewCPUBackend()
	x := []float64{}
	out, err := b.Softmax(x, 1)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(out) != 0 {
		t.Fatalf("expected empty output, got %d", len(out))
	}
}

func TestCPUBackendReluAllNegative(t *testing.T) {
	b := NewCPUBackend()
	x := []float64{-1, -2, -3}
	out := b.Relu(x)
	for i, v := range out {
		if v != 0 {
			t.Errorf("Relu[%d] = %v, want 0", i, v)
		}
	}
}

func TestCPUBackendReluAllPositive(t *testing.T) {
	b := NewCPUBackend()
	x := []float64{1, 2, 3}
	out := b.Relu(x)
	for i, v := range out {
		if v != x[i] {
			t.Errorf("Relu[%d] = %v, want %v", i, v, x[i])
		}
	}
}

func TestCPUBackendAddEmpty(t *testing.T) {
	b := NewCPUBackend()
	out, err := b.Add([]float64{}, []float64{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(out) != 0 {
		t.Fatalf("expected empty output, got %d", len(out))
	}
}

func TestCPUBackendMatMulEmpty(t *testing.T) {
	b := NewCPUBackend()
	out, err := b.MatMul([]float64{}, []float64{}, 0, 0, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(out) != 0 {
		t.Fatalf("expected empty output, got %d", len(out))
	}
}

func TestCPUBackendSupportedDtypesContains(t *testing.T) {
	b := NewCPUBackend()
	dtypes := b.SupportedDtypes()
	found := false
	for _, dt := range dtypes {
		if dt == "float32" {
			found = true
			break
		}
	}
	if !found {
		t.Fatal("expected 'float32' in supported dtypes")
	}
}

func TestCPUBackendMatMul1x1(t *testing.T) {
	b := NewCPUBackend()
	a := []float64{2.0}
	bb := []float64{3.0}
	out, err := b.MatMul(a, bb, 1, 1, 1)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(out) != 1 || math.Abs(out[0]-6.0) > 1e-9 {
		t.Fatalf("expected [6.0], got %v", out)
	}
}

func TestCPUBackendAddSingleElement(t *testing.T) {
	b := NewCPUBackend()
	a := []float64{1.0}
	bb := []float64{2.0}
	out, err := b.Add(a, bb)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(out) != 1 || out[0] != 3.0 {
		t.Fatalf("expected [3.0], got %v", out)
	}
}

func TestCPUBackendSoftmaxLargeValues(t *testing.T) {
	b := NewCPUBackend()
	x := []float64{1000, 1001, 1002}
	out, err := b.Softmax(x, 1)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	var sum float64
	for _, v := range out {
		sum += v
	}
	if math.Abs(sum-1.0) > 1e-6 {
		t.Fatalf("Softmax sum = %v, want 1.0", sum)
	}
}

func TestCPUBackendReluZero(t *testing.T) {
	b := NewCPUBackend()
	x := []float64{0, 0, 0}
	out := b.Relu(x)
	for _, v := range out {
		if v != 0 {
			t.Fatalf("expected 0, got %v", v)
		}
	}
}

func TestCPUBackendMatMulRectangular(t *testing.T) {
	b := NewCPUBackend()
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8, 9, 10}
	out, err := b.MatMul(a, bb, 2, 3, 2)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(out) != 6 {
		t.Fatalf("expected 6 elements, got %d", len(out))
	}
}
