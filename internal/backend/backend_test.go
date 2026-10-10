package backend

import (
	"math"
	"sync"
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

func TestRegisterAndGetBackend(t *testing.T) {
	RegisterBackend("cpu", NewCPUBackend())
	b, ok := GetBackend("cpu")
	if !ok || b == nil {
		t.Fatal("expected cpu backend")
	}
}

func TestDefaultBackend(t *testing.T) {
	RegisterBackend("cpu", NewCPUBackend())
	b := DefaultBackend()
	if b == nil || b.Name() != "cpu" {
		t.Fatal("expected default cpu backend")
	}
}

func TestListBackends(t *testing.T) {
	RegisterBackend("cpu", NewCPUBackend())
	names := ListBackends()
	found := false
	for _, n := range names {
		if n == "cpu" {
			found = true
		}
	}
	if !found {
		t.Fatal("expected cpu in backends list")
	}
}

func TestCPUThreadPool(t *testing.T) {
	pool := NewCPUThreadPool(2)
	defer pool.Shutdown()
	var wg sync.WaitGroup
	wg.Add(1)
	pool.Submit(func() { wg.Done() })
	wg.Wait()
}

func TestVecAdd(t *testing.T) {
	a := []float64{1, 2, 3}
	b := []float64{4, 5, 6}
	out, err := VecAdd(a, b, NewCPUThreadPool(2))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{5, 7, 9}
	for i := range expected {
		if out[i] != expected[i] {
			t.Errorf("VecAdd[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestVecMatMul(t *testing.T) {
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8}
	out, err := VecMatMul(a, bb, 2, 2, 2, NewCPUThreadPool(2))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{19, 22, 43, 50}
	for i := range expected {
		if math.Abs(out[i]-expected[i]) > 1e-9 {
			t.Errorf("VecMatMul[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestMemoryLayoutRowMajor(t *testing.T) {
	layout := NewRowMajor([]int{2, 3})
	if layout.Layout != RowMajorLayout {
		t.Fatalf("expected row major, got %s", layout.Layout)
	}
	if len(layout.Strides) != 2 {
		t.Fatalf("expected 2 strides, got %d", len(layout.Strides))
	}
}

func TestMemoryLayoutColumnMajor(t *testing.T) {
	layout := NewColumnMajor([]int{2, 3})
	if layout.Layout != ColumnMajorLayout {
		t.Fatalf("expected column major, got %s", layout.Layout)
	}
	if len(layout.Strides) != 2 {
		t.Fatalf("expected 2 strides, got %d", len(layout.Strides))
	}
}

func TestDeviceString(t *testing.T) {
	if DeviceCPU.String() != "cpu" {
		t.Fatalf("expected cpu, got %s", DeviceCPU.String())
	}
	if DeviceCUDA.String() != "cuda" {
		t.Fatalf("expected cuda, got %s", DeviceCUDA.String())
	}
}

func TestSchedulerBackend(t *testing.T) {
	b := NewCPUBackend()
	sb := NewSchedulerBackend(b, 2)
	defer sb.Close()
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8}
	out, err := sb.MatMulAsync(a, bb, 2, 2, 2)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{19, 22, 43, 50}
	for i := range expected {
		if math.Abs(out[i]-expected[i]) > 1e-9 {
			t.Errorf("MatMulAsync[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestVecAddShapeMismatch(t *testing.T) {
	_, err := VecAdd([]float64{1, 2}, []float64{1}, NewCPUThreadPool(1))
	if err == nil {
		t.Fatal("expected shape mismatch error")
	}
}

func TestVecMatMulInvalidDims(t *testing.T) {
	_, err := VecMatMul([]float64{1, 2}, []float64{1}, 2, 2, 2, NewCPUThreadPool(1))
	if err == nil {
		t.Fatal("expected invalid dims error")
	}
}

func TestCPUBackendSoftmaxInvalidDim(t *testing.T) {
	b := NewCPUBackend()
	// dim=0 and dim=1 are both valid on a flat slice; only higher dims
	// are unsupported.
	_, err := b.Softmax([]float64{1, 2}, 2)
	if err == nil {
		t.Fatal("expected error for invalid dim")
	}
}

func TestCPUBackendMatMulInvalidDims(t *testing.T) {
	b := NewCPUBackend()
	_, err := b.MatMul([]float64{1, 2}, []float64{1}, 2, 2, 2)
	if err == nil {
		t.Fatal("expected invalid dims error")
	}
}

func TestRegisterBackendDefault(t *testing.T) {
	RegisterBackend("test_backend", NewCPUBackend())
	b, ok := GetBackend("test_backend")
	if !ok || b == nil {
		t.Fatal("expected registered backend")
	}
	if DefaultBackend() == nil || DefaultBackend().Name() != "cpu" {
		t.Fatal("expected default cpu backend")
	}
}

func TestMemoryLayoutSingleDimension(t *testing.T) {
	layout := NewRowMajor([]int{4})
	if layout.Layout != RowMajorLayout {
		t.Fatalf("expected row major, got %s", layout.Layout)
	}
	if len(layout.Strides) != 1 || layout.Strides[0] != 1 {
		t.Fatalf("expected stride 1, got %v", layout.Strides)
	}
}

func TestMemoryLayoutEmptyShape(t *testing.T) {
	layout := NewRowMajor([]int{})
	if layout.Layout != RowMajorLayout {
		t.Fatalf("expected row major, got %s", layout.Layout)
	}
	if len(layout.Strides) != 0 {
		t.Fatalf("expected 0 strides for scalar, got %d", len(layout.Strides))
	}
}

func TestCPUThreadPoolShutdown(t *testing.T) {
	pool := NewCPUThreadPool(2)
	var wg sync.WaitGroup
	wg.Add(1)
	pool.Submit(func() { wg.Done() })
	wg.Wait()
	pool.Shutdown()
}

func TestSchedulerBackendAddAsync(t *testing.T) {
	b := NewCPUBackend()
	sb := NewSchedulerBackend(b, 2)
	defer sb.Close()
	a := []float64{1, 2, 3}
	bb := []float64{4, 5, 6}
	out, err := sb.AddAsync(a, bb)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{5, 7, 9}
	for i := range expected {
		if out[i] != expected[i] {
			t.Errorf("AddAsync[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestVecAddWithNilPool(t *testing.T) {
	a := []float64{1, 2, 3}
	b := []float64{4, 5, 6}
	out, err := VecAdd(a, b, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{5, 7, 9}
	for i := range expected {
		if out[i] != expected[i] {
			t.Errorf("VecAdd[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestVecMatMulWithNilPool(t *testing.T) {
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8}
	out, err := VecMatMul(a, bb, 2, 2, 2, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{19, 22, 43, 50}
	for i := range expected {
		if math.Abs(out[i]-expected[i]) > 1e-9 {
			t.Errorf("VecMatMul[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestBackendCapabilitiesStruct(t *testing.T) {
	caps := Capabilities{
		Devices:      []Device{DeviceCPU},
		Dtypes:       []string{"float32"},
		MaxMemory:    1024,
		ThreadCount:  4,
		HasVectorize: true,
		HasStreams:   false,
	}
	if len(caps.Devices) != 1 {
		t.Fatalf("expected 1 device, got %d", len(caps.Devices))
	}
	if caps.MaxMemory != 1024 {
		t.Fatalf("expected max memory 1024, got %d", caps.MaxMemory)
	}
}

func TestDeviceAllValues(t *testing.T) {
	devices := []Device{DeviceCPU, DeviceCUDA, DeviceROCm, DeviceMetal, DeviceOpenCL}
	for _, d := range devices {
		s := d.String()
		if s == "unknown" {
			t.Fatalf("expected valid device string for %d, got %s", d, s)
		}
	}
}

func TestMemoryLayoutColumnMajorStrides(t *testing.T) {
	layout := NewColumnMajor([]int{2, 3})
	expectedStrides := []int{1, 2}
	for i, s := range expectedStrides {
		if layout.Strides[i] != s {
			t.Errorf("stride[%d] = %d, want %d", i, layout.Strides[i], s)
		}
	}
}

func TestMemoryLayoutRowMajorStrides(t *testing.T) {
	layout := NewRowMajor([]int{2, 3})
	expectedStrides := []int{3, 1}
	for i, s := range expectedStrides {
		if layout.Strides[i] != s {
			t.Errorf("stride[%d] = %d, want %d", i, layout.Strides[i], s)
		}
	}
}

func TestSchedulerBackendCloseIdempotent(t *testing.T) {
	b := NewCPUBackend()
	sb := NewSchedulerBackend(b, 2)
	sb.Close()
	sb.Close()
}

func TestListBackendsEmpty(t *testing.T) {
	names := ListBackends()
	_ = names
}

