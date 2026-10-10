package backend_test

import (
	"sync"
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
)

func TestBackendRegisterAndGet(t *testing.T) {
	backend.RegisterBackend("cpu", backend.NewCPUBackend())
	b, ok := backend.GetBackend("cpu")
	if !ok || b == nil {
		t.Fatal("expected cpu backend")
	}
}

func TestBackendDefaultBackend(t *testing.T) {
	backend.RegisterBackend("cpu", backend.NewCPUBackend())
	b := backend.DefaultBackend()
	if b == nil || b.Name() != "cpu" {
		t.Fatal("expected default cpu backend")
	}
}

func TestBackendListBackends(t *testing.T) {
	backend.RegisterBackend("cpu", backend.NewCPUBackend())
	names := backend.ListBackends()
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

func TestBackendCPUThreadPool(t *testing.T) {
	pool := backend.NewCPUThreadPool(2)
	defer pool.Shutdown()
	var wg sync.WaitGroup
	wg.Add(1)
	pool.Submit(func() { wg.Done() })
	wg.Wait()
}

func TestBackendVecAdd(t *testing.T) {
	a := []float64{1, 2, 3}
	b := []float64{4, 5, 6}
	out, err := backend.VecAdd(a, b, backend.NewCPUThreadPool(2))
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

func TestBackendVecMatMul(t *testing.T) {
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8}
	out, err := backend.VecMatMul(a, bb, 2, 2, 2, backend.NewCPUThreadPool(2))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{19, 22, 43, 50}
	for i := range expected {
		if out[i] != expected[i] {
			t.Errorf("VecMatMul[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestBackendMemoryLayoutRowMajor(t *testing.T) {
	layout := backend.NewRowMajor([]int{2, 3})
	if layout.Layout != backend.RowMajorLayout {
		t.Fatalf("expected row major, got %s", layout.Layout)
	}
	if len(layout.Strides) != 2 {
		t.Fatalf("expected 2 strides, got %d", len(layout.Strides))
	}
}

func TestBackendMemoryLayoutColumnMajor(t *testing.T) {
	layout := backend.NewColumnMajor([]int{2, 3})
	if layout.Layout != backend.ColumnMajorLayout {
		t.Fatalf("expected column major, got %s", layout.Layout)
	}
	if len(layout.Strides) != 2 {
		t.Fatalf("expected 2 strides, got %d", len(layout.Strides))
	}
}

func TestBackendDeviceString(t *testing.T) {
	if backend.DeviceCPU.String() != "cpu" {
		t.Fatalf("expected cpu, got %s", backend.DeviceCPU.String())
	}
	if backend.DeviceCUDA.String() != "cuda" {
		t.Fatalf("expected cuda, got %s", backend.DeviceCUDA.String())
	}
}

func TestBackendSchedulerBackend(t *testing.T) {
	b := backend.NewCPUBackend()
	sb := backend.NewSchedulerBackend(b, 2)
	defer sb.Close()
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8}
	out, err := sb.MatMulAsync(a, bb, 2, 2, 2)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{19, 22, 43, 50}
	for i := range expected {
		if out[i] != expected[i] {
			t.Errorf("MatMulAsync[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestBackendVecAddShapeMismatch(t *testing.T) {
	_, err := backend.VecAdd([]float64{1, 2}, []float64{1}, backend.NewCPUThreadPool(1))
	if err == nil {
		t.Fatal("expected shape mismatch error")
	}
}

func TestBackendVecMatMulInvalidDims(t *testing.T) {
	_, err := backend.VecMatMul([]float64{1, 2}, []float64{1}, 2, 2, 2, backend.NewCPUThreadPool(1))
	if err == nil {
		t.Fatal("expected invalid dims error")
	}
}

func TestBackendCPUBackendSoftmaxInvalidDim(t *testing.T) {
	b := backend.NewCPUBackend()
	// dim=0 and dim=1 are valid on a flat slice; dim=2 is not.
	_, err := b.Softmax([]float64{1, 2}, 2)
	if err == nil {
		t.Fatal("expected error for invalid dim")
	}
}

func TestBackendCPUBackendAddShapeMismatch(t *testing.T) {
	b := backend.NewCPUBackend()
	_, err := b.Add([]float64{1, 2}, []float64{1})
	if err == nil {
		t.Fatal("expected shape mismatch error")
	}
}

func TestBackendCPUBackendMatMulInvalidDims(t *testing.T) {
	b := backend.NewCPUBackend()
	_, err := b.MatMul([]float64{1, 2}, []float64{1}, 2, 2, 2)
	if err == nil {
		t.Fatal("expected invalid dims error")
	}
}

func TestBackendRegisterBackendDefault(t *testing.T) {
	backend.RegisterBackend("test_backend", backend.NewCPUBackend())
	b, ok := backend.GetBackend("test_backend")
	if !ok || b == nil {
		t.Fatal("expected registered backend")
	}
	if backend.DefaultBackend() == nil || backend.DefaultBackend().Name() != "cpu" {
		t.Fatal("expected default cpu backend")
	}
}

func TestBackendMemoryLayoutSingleDimension(t *testing.T) {
	layout := backend.NewRowMajor([]int{4})
	if layout.Layout != backend.RowMajorLayout {
		t.Fatalf("expected row major, got %s", layout.Layout)
	}
	if len(layout.Strides) != 1 || layout.Strides[0] != 1 {
		t.Fatalf("expected stride 1, got %v", layout.Strides)
	}
}

func TestBackendMemoryLayoutEmptyShape(t *testing.T) {
	layout := backend.NewRowMajor([]int{})
	if layout.Layout != backend.RowMajorLayout {
		t.Fatalf("expected row major, got %s", layout.Layout)
	}
	if len(layout.Strides) != 0 {
		t.Fatalf("expected 0 strides for scalar, got %d", len(layout.Strides))
	}
}

func TestBackendCPUThreadPoolShutdown(t *testing.T) {
	pool := backend.NewCPUThreadPool(2)
	var wg sync.WaitGroup
	wg.Add(1)
	pool.Submit(func() { wg.Done() })
	wg.Wait()
	pool.Shutdown()
}

func TestBackendSchedulerBackendAddAsync(t *testing.T) {
	b := backend.NewCPUBackend()
	sb := backend.NewSchedulerBackend(b, 2)
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

func TestBackendVecAddWithNilPool(t *testing.T) {
	a := []float64{1, 2, 3}
	b := []float64{4, 5, 6}
	out, err := backend.VecAdd(a, b, nil)
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

func TestBackendVecMatMulWithNilPool(t *testing.T) {
	a := []float64{1, 2, 3, 4}
	bb := []float64{5, 6, 7, 8}
	out, err := backend.VecMatMul(a, bb, 2, 2, 2, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := []float64{19, 22, 43, 50}
	for i := range expected {
		if out[i] != expected[i] {
			t.Errorf("VecMatMul[%d] = %v, want %v", i, out[i], expected[i])
		}
	}
}

func TestBackendCapabilitiesStruct(t *testing.T) {
	caps := backend.Capabilities{
		Devices:      []backend.Device{backend.DeviceCPU},
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

func TestBackendDeviceAllValues(t *testing.T) {
	devices := []backend.Device{backend.DeviceCPU, backend.DeviceCUDA, backend.DeviceROCm, backend.DeviceMetal, backend.DeviceOpenCL}
	for _, d := range devices {
		s := d.String()
		if s == "unknown" {
			t.Fatalf("expected valid device string for %d, got %s", d, s)
		}
	}
}

func TestBackendMemoryLayoutColumnMajorStrides(t *testing.T) {
	layout := backend.NewColumnMajor([]int{2, 3})
	expectedStrides := []int{1, 2}
	for i, s := range expectedStrides {
		if layout.Strides[i] != s {
			t.Errorf("stride[%d] = %d, want %d", i, layout.Strides[i], s)
		}
	}
}

func TestBackendMemoryLayoutRowMajorStrides(t *testing.T) {
	layout := backend.NewRowMajor([]int{2, 3})
	expectedStrides := []int{3, 1}
	for i, s := range expectedStrides {
		if layout.Strides[i] != s {
			t.Errorf("stride[%d] = %d, want %d", i, layout.Strides[i], s)
		}
	}
}

func TestBackendSchedulerBackendCloseIdempotent(t *testing.T) {
	b := backend.NewCPUBackend()
	sb := backend.NewSchedulerBackend(b, 2)
	sb.Close()
	sb.Close()
}

func TestBackendListBackendsEmpty(t *testing.T) {
	names := backend.ListBackends()
	_ = names
}
