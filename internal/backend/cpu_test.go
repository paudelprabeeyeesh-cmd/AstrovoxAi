package backend

import (
	"math"
	"sync"
	"testing"
)

// This file covers the CPU backend, the thread pool, memory layout, and
// the backend registry, all in-package so internals stay testable.

// ---------------------------------------------------------------------------
// CPU backend: ops
// ---------------------------------------------------------------------------

func TestCPUBackendNameAndDtypes(t *testing.T) {
	b := NewCPUBackend()
	if b.Name() != "cpu" {
		t.Errorf("Name() = %q, want cpu", b.Name())
	}
	dtypes := b.SupportedDtypes()
	if len(dtypes) == 0 {
		t.Fatal("expected non-empty dtype list")
	}
	hasFloat64 := false
	for _, d := range dtypes {
		if d == "float64" {
			hasFloat64 = true
		}
	}
	if !hasFloat64 {
		t.Errorf("cpu backend must support float64, got %v", dtypes)
	}
}

func TestCPUBackendMatMul(t *testing.T) {
	b := NewCPUBackend()
	a := []float64{1, 2, 3, 4}
	m := []float64{5, 6, 7, 8}
	out, err := b.MatMul(a, m, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	want := []float64{19, 22, 43, 50}
	for i, v := range out {
		if math.Abs(v-want[i]) > 1e-9 {
			t.Errorf("element %d: got %v, want %v", i, v, want[i])
		}
	}
}

func TestCPUBackendMatMul1x1(t *testing.T) {
	b := NewCPUBackend()
	out, err := b.MatMul([]float64{3}, []float64{4}, 1, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 || out[0] != 12 {
		t.Errorf("got %v, want [12]", out)
	}
}

func TestCPUBackendMatMulRectangular(t *testing.T) {
	b := NewCPUBackend()
	a := make([]float64, 2*3)
	m := make([]float64, 3*4)
	out, err := b.MatMul(a, m, 2, 4, 3)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 8 {
		t.Errorf("expected 8 outputs, got %d", len(out))
	}
}

func TestCPUBackendMatMulInvalidDims(t *testing.T) {
	b := NewCPUBackend()
	if _, err := b.MatMul([]float64{1, 2}, []float64{1, 2}, 3, 3, 3); err == nil {
		t.Error("expected error for mismatched a")
	}
	if _, err := b.MatMul([]float64{1, 2, 3, 4}, []float64{1}, 2, 2, 2); err == nil {
		t.Error("expected error for mismatched b")
	}
}

func TestCPUBackendMatMulEmpty(t *testing.T) {
	b := NewCPUBackend()
	out, err := b.MatMul(nil, nil, 0, 0, 0)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 0 {
		t.Errorf("expected empty output, got %v", out)
	}
}

func TestCPUBackendAdd(t *testing.T) {
	b := NewCPUBackend()
	out, err := b.Add([]float64{1, 2, 3}, []float64{4, 5, 6})
	if err != nil {
		t.Fatal(err)
	}
	want := []float64{5, 7, 9}
	for i, v := range out {
		if v != want[i] {
			t.Errorf("element %d: got %v, want %v", i, v, want[i])
		}
	}
}

func TestCPUBackendAddSingleElement(t *testing.T) {
	b := NewCPUBackend()
	out, err := b.Add([]float64{1}, []float64{2})
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 || out[0] != 3 {
		t.Errorf("got %v", out)
	}
}

func TestCPUBackendAddShapeMismatch(t *testing.T) {
	b := NewCPUBackend()
	if _, err := b.Add([]float64{1, 2}, []float64{1}); err == nil {
		t.Error("expected shape mismatch error")
	}
}

func TestCPUBackendAddEmpty(t *testing.T) {
	b := NewCPUBackend()
	out, err := b.Add(nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 0 {
		t.Errorf("expected empty output, got %v", out)
	}
}

func TestCPUBackendRelu(t *testing.T) {
	b := NewCPUBackend()
	x := b.Relu([]float64{-1, 0, 1, 2, -3})
	want := []float64{0, 0, 1, 2, 0}
	for i, v := range x {
		if v != want[i] {
			t.Errorf("element %d: got %v, want %v", i, v, want[i])
		}
	}
}

func TestCPUBackendReluAllNegative(t *testing.T) {
	b := NewCPUBackend()
	for _, v := range b.Relu([]float64{-1, -2, -3}) {
		if v != 0 {
			t.Errorf("expected 0, got %v", v)
		}
	}
}

func TestCPUBackendReluAllPositive(t *testing.T) {
	b := NewCPUBackend()
	in := []float64{1, 2, 3}
	out := b.Relu(in)
	for i, v := range out {
		if v != in[i] {
			t.Errorf("element %d: got %v, want %v", i, v, in[i])
		}
	}
}

func TestCPUBackendSoftmax(t *testing.T) {
	b := NewCPUBackend()
	out, err := b.Softmax([]float64{1, 2, 3}, 0)
	if err != nil {
		t.Fatal(err)
	}
	sum := 0.0
	for _, v := range out {
		sum += v
	}
	if math.Abs(sum-1) > 1e-9 {
		t.Errorf("sum = %v, want 1", sum)
	}
	if out[2] <= out[0] {
		t.Error("softmax must preserve ordering")
	}
}

func TestCPUBackendSoftmaxLargeValues(t *testing.T) {
	b := NewCPUBackend()
	out, err := b.Softmax([]float64{1000, 1001}, 0)
	if err != nil {
		t.Fatal(err)
	}
	sum := 0.0
	for _, v := range out {
		if math.IsNaN(v) || math.IsInf(v, 0) {
			t.Fatalf("softmax produced %v for large inputs: %v", v, out)
		}
		sum += v
	}
	if math.Abs(sum-1) > 1e-9 {
		t.Errorf("sum = %v, want 1", sum)
	}
}

func TestCPUBackendSoftmaxEmpty(t *testing.T) {
	b := NewCPUBackend()
	if _, err := b.Softmax(nil, 0); err == nil {
		t.Error("expected error for empty input")
	}
}

// dim=0 and dim=1 are both valid on a flat slice; higher dims are not.
func TestCPUBackendSoftmaxDim(t *testing.T) {
	b := NewCPUBackend()
	for _, dim := range []int{0, 1} {
		if _, err := b.Softmax([]float64{1, 2, 3}, dim); err != nil {
			t.Errorf("dim %d: %v", dim, err)
		}
	}
	if _, err := b.Softmax([]float64{1, 2}, 2); err == nil {
		t.Error("expected error for dim=2")
	}
}

// ---------------------------------------------------------------------------
// CPU backend: thread pool and vector ops
// ---------------------------------------------------------------------------

func TestCPUThreadPoolExecutesAllTasks(t *testing.T) {
	pool := NewCPUThreadPool(4)
	const tasks = 100
	var mu sync.Mutex
	done := 0
	for i := 0; i < tasks; i++ {
		pool.Submit(func() {
			mu.Lock()
			done++
			mu.Unlock()
		})
	}
	pool.Wait()
	mu.Lock()
	defer mu.Unlock()
	if done != tasks {
		t.Errorf("completed %d of %d tasks", done, tasks)
	}
}

func TestCPUThreadPoolShutdownIdempotent(t *testing.T) {
	pool := NewCPUThreadPool(2)
	pool.Submit(func() {})
	pool.Shutdown()
	pool.Shutdown() // must not panic
}

func TestCPUThreadPoolSingleWorker(t *testing.T) {
	pool := NewCPUThreadPool(1)
	done := make(chan bool, 1)
	pool.Submit(func() { done <- true })
	if !<-done {
		t.Error("task did not run")
	}
	pool.Shutdown()
}

func TestVecAddWithPool(t *testing.T) {
	pool := NewCPUThreadPool(2)
	defer pool.Shutdown()
	out, err := VecAdd([]float64{1, 2, 3, 4}, []float64{10, 20, 30, 40}, pool)
	if err != nil {
		t.Fatal(err)
	}
	want := []float64{11, 22, 33, 44}
	for i, v := range out {
		if v != want[i] {
			t.Errorf("element %d: got %v, want %v", i, v, want[i])
		}
	}
}

func TestVecAddWithNilPool(t *testing.T) {
	out, err := VecAdd([]float64{1, 1}, []float64{2, 3}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if out[0] != 3 || out[1] != 4 {
		t.Errorf("got %v", out)
	}
}

func TestVecAddShapeMismatch(t *testing.T) {
	if _, err := VecAdd([]float64{1, 2}, []float64{1}, nil); err == nil {
		t.Error("expected shape mismatch error")
	}
}

func TestVecAddEmpty(t *testing.T) {
	out, err := VecAdd(nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 0 {
		t.Errorf("expected empty output, got %v", out)
	}
}

func TestVecMatMulWithPool(t *testing.T) {
	pool := NewCPUThreadPool(4)
	defer pool.Shutdown()
	a := []float64{1, 2, 3, 4}
	m := []float64{5, 6, 7, 8}
	out, err := VecMatMul(a, m, 2, 2, 2, pool)
	if err != nil {
		t.Fatal(err)
	}
	want := []float64{19, 22, 43, 50}
	for i, v := range out {
		if v != want[i] {
			t.Errorf("element %d: got %v, want %v", i, v, want[i])
		}
	}
}

func TestVecMatMulWithNilPool(t *testing.T) {
	out, err := VecMatMul([]float64{1, 2, 3, 4}, []float64{5, 6, 7, 8}, 2, 2, 2, nil)
	if err != nil {
		t.Fatal(err)
	}
	if out[0] != 19 {
		t.Errorf("got %v", out)
	}
}

func TestVecMatMulInvalidDims(t *testing.T) {
	if _, err := VecMatMul([]float64{1}, []float64{1, 2}, 2, 2, 2, nil); err == nil {
		t.Error("expected dimension error")
	}
}

// ---------------------------------------------------------------------------
// Memory layout
// ---------------------------------------------------------------------------

func TestNewRowMajor(t *testing.T) {
	ml := NewRowMajor([]int{2, 3, 4})
	want := []int{12, 4, 1}
	if ml.Layout != RowMajorLayout {
		t.Errorf("layout = %q, want %q", ml.Layout, RowMajorLayout)
	}
	for i, w := range want {
		if ml.Strides[i] != w {
			t.Errorf("stride %d: got %d, want %d", i, ml.Strides[i], w)
		}
	}
}

func TestNewColumnMajor(t *testing.T) {
	ml := NewColumnMajor([]int{2, 3, 4})
	want := []int{1, 2, 6}
	if ml.Layout != ColumnMajorLayout {
		t.Errorf("layout = %q, want %q", ml.Layout, ColumnMajorLayout)
	}
	for i, w := range want {
		if ml.Strides[i] != w {
			t.Errorf("stride %d: got %d, want %d", i, ml.Strides[i], w)
		}
	}
}

func TestNewRowMajorSingleDimension(t *testing.T) {
	ml := NewRowMajor([]int{5})
	if len(ml.Strides) != 1 || ml.Strides[0] != 1 {
		t.Errorf("1-D strides = %v", ml.Strides)
	}
}

func TestNewColumnMajorSingleDimension(t *testing.T) {
	ml := NewColumnMajor([]int{5})
	if len(ml.Strides) != 1 || ml.Strides[0] != 1 {
		t.Errorf("1-D strides = %v", ml.Strides)
	}
}

func TestNewMemoryLayoutEmptyShape(t *testing.T) {
	if ml := NewRowMajor(nil); len(ml.Strides) != 0 {
		t.Errorf("expected no strides for an empty shape, got %v", ml.Strides)
	}
	if ml := NewColumnMajor(nil); len(ml.Strides) != 0 {
		t.Errorf("expected no strides for an empty shape, got %v", ml.Strides)
	}
}

func TestDeviceStrings(t *testing.T) {
	devices := []Device{DeviceCPU, DeviceCUDA, DeviceROCm, DeviceMetal, DeviceOpenCL}
	seen := map[string]bool{}
	for _, d := range devices {
		s := d.String()
		if s == "" || s == "unknown" {
			t.Errorf("device %d has no name: %q", int(d), s)
		}
		if seen[s] {
			t.Errorf("device %d duplicates name %q", int(d), s)
		}
		seen[s] = true
	}
}

func TestDeviceUnknown(t *testing.T) {
	if Device(99).String() != "unknown" {
		t.Error("expected unknown for an out-of-range device")
	}
}

func TestCapabilitiesStruct(t *testing.T) {
	caps := Capabilities{
		Devices:      []Device{DeviceCPU},
		Dtypes:       []string{"float64"},
		MaxMemory:    1024,
		ThreadCount:  4,
		HasVectorize: true,
		HasStreams:   true,
	}
	if len(caps.Devices) != 1 || caps.MaxMemory != 1024 || !caps.HasVectorize {
		t.Error("capabilities fields")
	}
	// The zero value must be usable.
	var zero Capabilities
	if zero.MaxMemory != 0 || zero.ThreadCount != 0 {
		t.Error("zero value")
	}
}

// ---------------------------------------------------------------------------
// Scheduler backend bridge
// ---------------------------------------------------------------------------

func TestSchedulerBackendAsync(t *testing.T) {
	sb := NewSchedulerBackend(NewCPUBackend(), 4)
	defer sb.Close()

	add, err := sb.AddAsync([]float64{1, 2}, []float64{3, 4})
	if err != nil {
		t.Fatal(err)
	}
	if add[0] != 4 {
		t.Errorf("got %v", add)
	}

	product, err := sb.MatMulAsync([]float64{1, 2, 3, 4}, []float64{5, 6, 7, 8}, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	if product[0] != 19 {
		t.Errorf("got %v", product)
	}
}

func TestSchedulerBackendCloseIdempotent(t *testing.T) {
	sb := NewSchedulerBackend(NewCPUBackend(), 2)
	sb.Close()
	sb.Close() // must not panic
}

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

func TestRegisterAndGetBackend(t *testing.T) {
	RegisterBackend("cpu", NewCPUBackend())
	b, ok := GetBackend("cpu")
	if !ok || b == nil {
		t.Fatal("expected the cpu backend")
	}
	if b.Name() != "cpu" {
		t.Errorf("got %q", b.Name())
	}
	if _, ok := GetBackend("missing"); ok {
		t.Error("expected not found")
	}
}

func TestDefaultBackend(t *testing.T) {
	RegisterBackend("cpu", NewCPUBackend())
	b := DefaultBackend()
	if b == nil || b.Name() != "cpu" {
		t.Error("expected cpu as the default backend")
	}
}

func TestRegisterBackendSetsDefaultOnce(t *testing.T) {
	// The first registered backend becomes the default; later ones do not
	// change it. The global registry starts empty in a fresh test binary.
	RegisterBackend("cpu", NewCPUBackend())
	RegisterBackend("cuda", &stubBackend{name: "cuda"})
	if b := DefaultBackend(); b.Name() != "cpu" {
		t.Errorf("expected cpu to remain the default, got %q", b.Name())
	}
	if got := len(ListBackends()); got < 1 {
		t.Errorf("expected registered backends, got %d", got)
	}
}

func TestRegisterOverwritesByName(t *testing.T) {
	RegisterBackend("cpu", NewCPUBackend())
	RegisterBackend("cpu", &stubBackend{name: "cpu-override"})
	b, _ := GetBackend("cpu")
	if b.Name() != "cpu-override" {
		t.Errorf("expected the re-registered backend, got %q", b.Name())
	}
}

// stubBackend is a minimal Backend for registry tests.
type stubBackend struct{ name string }

func (s *stubBackend) Name() string              { return s.name }
func (s *stubBackend) SupportedDtypes() []string { return []string{"float64"} }
func (s *stubBackend) MatMul(a, b []float64, m, n, k int) ([]float64, error) {
	return nil, nil
}
func (s *stubBackend) Add(a, b []float64) ([]float64, error) { return nil, nil }
func (s *stubBackend) Relu(x []float64) []float64            { return x }
func (s *stubBackend) Softmax(x []float64, dim int) ([]float64, error) {
	return x, nil
}
