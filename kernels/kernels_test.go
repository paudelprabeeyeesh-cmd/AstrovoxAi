package kernels

import (
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
)

// floatView adapts a flat slice to TensorView.
type floatView struct {
	shape []int
	data  []float64
}

func (f floatView) DType() string { return "float64" }
func (f floatView) Shape() []int  { return f.shape }
func (f floatView) Data() any     { return f.data }

func view(shape []int, data ...float64) floatView {
	return floatView{shape: shape, data: data}
}

func TestVecAddKernel(t *testing.T) {
	a := view([]int{3}, 1, 2, 3)
	b := view([]int{3}, 10, 20, 30)
	out := view([]int{3}, 0, 0, 0)
	k := VecAddKernel{}
	if err := k.Execute([]TensorView{a, b}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	want := []float64{11, 22, 33}
	for i, v := range out.data {
		if v != want[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, want[i])
		}
	}
}

func TestVecMulKernel(t *testing.T) {
	a := view([]int{3}, 1, 2, 3)
	b := view([]int{3}, 10, 20, 30)
	out := view([]int{3}, 0, 0, 0)
	if err := (VecMulKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	want := []float64{10, 40, 90}
	for i, v := range out.data {
		if v != want[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, want[i])
		}
	}
}

func TestScaleKernel(t *testing.T) {
	a := view([]int{3}, 1, 2, 3)
	out := view([]int{3}, 0, 0, 0)
	err := (ScaleKernel{}).Execute([]TensorView{a}, []TensorView{out},
		map[string]any{"scalar": 2.5})
	if err != nil {
		t.Fatal(err)
	}
	want := []float64{2.5, 5, 7.5}
	for i, v := range out.data {
		if v != want[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, want[i])
		}
	}
}

func TestScaleMissingAttr(t *testing.T) {
	a := view([]int{3}, 1, 2, 3)
	out := view([]int{3}, 0, 0, 0)
	if err := (ScaleKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err == nil {
		t.Fatal("expected missing attribute error")
	}
}

func TestReluKernel(t *testing.T) {
	a := view([]int{4}, -1, 0, 2, -3)
	out := view([]int{4}, 0, 0, 0, 0)
	if err := (ReluKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	want := []float64{0, 0, 2, 0}
	for i, v := range out.data {
		if v != want[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, want[i])
		}
	}
}

func TestTanhKernel(t *testing.T) {
	a := view([]int{2}, 0, 1)
	out := view([]int{2}, 0, 0)
	if err := (TanhKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != 0 {
		t.Fatalf("tanh(0) = %v, want 0", out.data[0])
	}
	if out.data[1] < 0.76 || out.data[1] > 0.77 {
		t.Fatalf("tanh(1) = %v, want ~0.7616", out.data[1])
	}
}

func TestSumKernel(t *testing.T) {
	a := view([]int{4}, 1, 2, 3, 4)
	out := view([]int{1}, 0)
	if err := (SumKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != 10 {
		t.Fatalf("sum = %v, want 10", out.data[0])
	}
}

func TestMatMulKernel(t *testing.T) {
	// A = [[1,2],[3,4]], B = [[5,6],[7,8]]
	// A@B = [[19,22],[43,50]]
	a := view([]int{2, 2}, 1, 2, 3, 4)
	b := view([]int{2, 2}, 5, 6, 7, 8)
	out := view([]int{2, 2}, 0, 0, 0, 0)
	if err := (MatMulKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	want := []float64{19, 22, 43, 50}
	for i, v := range out.data {
		if v != want[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, want[i])
		}
	}
}

func TestMatMulDimMismatch(t *testing.T) {
	a := view([]int{2, 3}, 1, 2, 3, 4, 5, 6)
	b := view([]int{2, 2}, 1, 2, 3, 4)
	out := view([]int{2, 2}, 0, 0, 0, 0)
	if err := (MatMulKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err == nil {
		t.Fatal("expected dimension mismatch error")
	}
}

func TestArityCheck(t *testing.T) {
	a := view([]int{1}, 1)
	out := view([]int{1}, 0)
	if err := (VecAddKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err == nil {
		t.Fatal("expected arity error")
	}
}

func TestRegistryLookup(t *testing.T) {
	k, err := Lookup(backend.DeviceCPU, "vec_add")
	if err != nil {
		t.Fatal(err)
	}
	if k.Name() != "vec_add" {
		t.Fatalf("name = %q, want vec_add", k.Name())
	}
	if k.Device() != backend.DeviceCPU {
		t.Fatalf("device = %v, want cpu", k.Device())
	}
	if _, err := Lookup(backend.DeviceCPU, "nonexistent"); err == nil {
		t.Fatal("expected not-found error")
	}
}

func TestLookupAnyFallback(t *testing.T) {
	// LookupAny prefers the requested device:
	// CUDA carries a registered stub.
	k, err := LookupAny(backend.DeviceCUDA, "vec_add")
	if err != nil {
		t.Fatal(err)
	}
	if k.Device() != backend.DeviceCUDA {
		t.Fatalf("device = %v, want cuda", k.Device())
	}
	// When the preferred device lacks the
	// kernel entirely, LookupAny falls back
	// to any device that has it.
	type cpuOnly struct{}
	MustRegister(cpuOnlyStub{})
	k, err = LookupAny(backend.DeviceCUDA, "cpu_only_test")
	if err != nil {
		t.Fatal(err)
	}
	if k.Device() != backend.DeviceCPU {
		t.Fatalf("device = %v, want cpu fallback", k.Device())
	}
}

// cpuOnlyStub is a CPU-only kernel used to
// verify LookupAny fallback.
type cpuOnlyStub struct{}

func (cpuOnlyStub) Name() string           { return "cpu_only_test" }
func (cpuOnlyStub) Device() backend.Device { return backend.DeviceCPU }
func (cpuOnlyStub) Execute([]TensorView, []TensorView, map[string]any) error {
	return nil
}

func TestGPUStub(t *testing.T) {
	k, err := Lookup(backend.DeviceCUDA, "matmul")
	if err != nil {
		t.Fatal(err)
	}
	if k.Device() != backend.DeviceCUDA {
		t.Fatalf("device = %v, want cuda", k.Device())
	}
	a := view([]int{1}, 1)
	out := view([]int{1}, 0)
	err = k.Execute([]TensorView{a}, []TensorView{out}, nil)
	if err == nil {
		t.Fatal("expected unimplemented error")
	}
}

func TestListForDevice(t *testing.T) {
	cpu := ListForDevice(backend.DeviceCPU)
	if len(cpu) < 7 {
		t.Fatalf("cpu kernels = %d, want >= 7", len(cpu))
	}
	cuda := ListForDevice(backend.DeviceCUDA)
	if len(cuda) != len(GPUKernelNames) {
		t.Fatalf("cuda stubs = %d, want %d", len(cuda), len(GPUKernelNames))
	}
}

func TestDispatcherCPU(t *testing.T) {
	d := NewDispatcher(backend.DeviceCPU)
	if d.Fallback {
		t.Fatal("cpu dispatcher should not fall back")
	}
	a := view([]int{2}, 1, 2)
	b := view([]int{2}, 3, 4)
	out := view([]int{2}, 0, 0)
	if err := d.ExecuteVecAdd(a, b, out); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != 4 || out.data[1] != 6 {
		t.Fatalf("vec_add = %v, want [4 6]", out.data)
	}
}

func TestDispatcherGPUFallback(t *testing.T) {
	d := NewDispatcher(backend.DeviceCUDA)
	if !d.Fallback {
		t.Fatal("cuda dispatcher should fall back to cpu")
	}
	a := view([]int{2}, 1, 2)
	b := view([]int{2}, 3, 4)
	out := view([]int{2}, 0, 0)
	// The CUDA stub reports unimplemented; the
	// dispatcher falls back to the CPU kernel.
	if err := d.ExecuteVecAdd(a, b, out); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != 4 || out.data[1] != 6 {
		t.Fatalf("vec_add = %v, want [4 6]", out.data)
	}
}

func TestDispatcherUnknownKernel(t *testing.T) {
	d := NewDispatcher(backend.DeviceCPU)
	a := view([]int{1}, 1)
	out := view([]int{1}, 0)
	if err := d.Run("nonexistent", []TensorView{a}, []TensorView{out}, nil); err == nil {
		t.Fatal("expected not-found error")
	}
}

func TestGemmBlockedCPU(t *testing.T) {
	// Exercise the blocked GEMM with sizes that
	// cross the block boundaries (block=96/256).
	m, n, k := 130, 140, 150
	a := make([]float64, m*k)
	b := make([]float64, k*n)
	out := make([]float64, m*n)
	for i := range a {
		a[i] = float64(i % 7)
	}
	for i := range b {
		b[i] = float64(i % 5)
	}
	gemmBlockedCPU(a, b, out, m, n, k)
	// Verify a few elements against the naive
	// definition.
	for _, tc := range [][2]int{{0, 0}, {m - 1, n - 1}, {65, 70}} {
		i, j := tc[0], tc[1]
		var want float64
		for p := 0; p < k; p++ {
			want += a[i*k+p] * b[p*n+j]
		}
		if out[i*n+j] != want {
			t.Fatalf("out[%d,%d] = %v, want %v", i, j, out[i*n+j], want)
		}
	}
}
