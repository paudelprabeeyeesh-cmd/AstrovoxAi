package backend

import (
	"math"
	"testing"
)

func TestWebGPUCreation(t *testing.T) {
	w, err := NewWebGPU(DefaultWebGPUAdapter())
	if err != nil {
		t.Fatal(err)
	}
	if w.Name() != "webgpu" {
		t.Errorf("got %s", w.Name())
	}
	if w.Available() {
		t.Error("no real GPU in CI, adapter should be unavailable")
	}
	if w.Adapter().String() == "" {
		t.Error("adapter summary")
	}
}

func TestWebGPUInvalidAdapter(t *testing.T) {
	if _, err := NewWebGPU(WebGPUAdapter{}); err == nil {
		t.Error("expected empty adapter error")
	}
}

func TestWebGPUBuffers(t *testing.T) {
	w, _ := NewWebGPU(DefaultWebGPUAdapter())
	b, err := w.CreateBuffer("params", 4096, WebGPUBufferUsageStorage|WebGPUBufferUsageCopyDst)
	if err != nil {
		t.Fatal(err)
	}
	if b.size != 4096 {
		t.Error("size")
	}
	if b.UsageString() != "STORAGE|COPY_DST" {
		t.Errorf("usage string: %s", b.UsageString())
	}
	if w.BufferCount() != 1 {
		t.Error("buffer count")
	}
	w.DestroyBuffer(b)
	if w.BufferCount() != 0 {
		t.Error("expected buffer released")
	}
}

func TestWebGPUBufferLimits(t *testing.T) {
	w, _ := NewWebGPU(DefaultWebGPUAdapter())
	if _, err := w.CreateBuffer("x", 0, WebGPUBufferUsageStorage); err == nil {
		t.Error("expected zero-size error")
	}
	l := w.Capabilities().MaxMemory
	_ = l
	// Use the adapter's own max buffer size to prove the limit is enforced.
	huge := uint64(w.adapter.Limits.maxBufferSize) + 1
	if _, err := w.CreateBuffer("big", huge, WebGPUBufferUsageStorage); err != ErrWebGPUBufferSize {
		t.Errorf("expected size error, got %v", err)
	}
}

func TestWebGPUPipelines(t *testing.T) {
	w, _ := NewWebGPU(DefaultWebGPUAdapter())
	p, err := w.CreatePipeline("matmul", "main", 64, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	if !p.compiled.Load() {
		t.Error("pipeline should compile")
	}
	if err := w.Dispatch(p, 16, 1, 1); err != nil {
		t.Fatal(err)
	}
	// Oversized workgroup must be rejected.
	if _, err := w.CreatePipeline("bad", "main", 99999, 1, 1); err == nil {
		t.Error("expected workgroup limit error")
	}
	// Too many invocations must be rejected.
	if _, err := w.CreatePipeline("bad2", "main", 256, 256, 1); err == nil {
		t.Error("expected invocation limit error")
	}
}

func TestWebGPUOps(t *testing.T) {
	w, _ := NewWebGPU(DefaultWebGPUAdapter())
	out, err := w.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	want := []float64{7, 10, 15, 22}
	for i, v := range out {
		if math.Abs(v-want[i]) > 1e-9 {
			t.Errorf("element %d: %f", i, v)
		}
	}
	sum, err := w.Add([]float64{1, 2}, []float64{3, 4})
	if err != nil {
		t.Fatal(err)
	}
	if sum[0] != 4 {
		t.Error("add")
	}
	x := w.Relu([]float64{-1, 2})
	if x[0] != 0 {
		t.Error("relu")
	}
	sm, err := w.Softmax([]float64{1, 2, 3}, 0)
	if err != nil {
		t.Fatal(err)
	}
	total := 0.0
	for _, v := range sm {
		total += v
	}
	if math.Abs(total-1) > 1e-9 {
		t.Error("softmax sum")
	}
	if _, err := w.Softmax(nil, 0); err == nil {
		t.Error("expected empty error")
	}
}

func TestWebGPUMatMulInvalid(t *testing.T) {
	w, _ := NewWebGPU(DefaultWebGPUAdapter())
	if _, err := w.MatMul([]float64{1}, []float64{1, 2}, 2, 2, 2); err == nil {
		t.Error("expected dimension error")
	}
}

func TestROCmCreation(t *testing.T) {
	r, err := NewROCmBackend(0)
	if err != nil {
		t.Fatal(err)
	}
	if r.Name() != "rocm" || r.GCNArch() != "gfx90a" {
		t.Error("rocm setup")
	}
	if r.Available() {
		t.Error("no AMD GPU in CI")
	}
	if _, err := NewROCmBackend(-1); err == nil {
		t.Error("expected device error")
	}
}

func TestROCmOps(t *testing.T) {
	r, _ := NewROCmBackend(0)
	out, _ := r.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	if out[0] != 7 || out[3] != 22 {
		t.Errorf("got %v", out)
	}
	if _, err := r.Add([]float64{1}, []float64{2}); err == nil {
		// 1 == 1 so this succeeds
		t.Log("add ok")
	}
	if _, err := r.Add([]float64{1, 2}, []float64{3}); err == nil {
		t.Error("expected mismatch error")
	}
	x := r.Relu([]float64{-2, 3})
	if x[0] != 0 || x[1] != 3 {
		t.Error("relu")
	}
	if _, err := r.Softmax([]float64{1, 2}, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := r.Softmax(nil, 0); err == nil {
		t.Error("expected empty error")
	}
	st := r.Stats()
	if st.MatMulOps.Load() != 1 || st.KernelLaunches.Load() != 1 {
		t.Error("stats")
	}
}

func TestOpenCLPlatform(t *testing.T) {
	p := DefaultOpenCLPlatform()
	if len(p.Devices) != 2 {
		t.Fatalf("expected 2 devices, got %d", len(p.Devices))
	}
	b, err := NewOpenCLBackend(p, 0)
	if err != nil {
		t.Fatal(err)
	}
	if b.Name() != "opencl" {
		t.Error("name")
	}
	// BestDevice should be the GPU (80 units > 16 units).
	if b.BestDevice().Name != "Sim GPU" {
		t.Errorf("expected GPU, got %s", b.BestDevice().Name)
	}
	if OpenCLDeviceTypeCPU.String() != "cpu" || OpenCLDeviceTypeGPU.String() != "gpu" {
		t.Error("device type strings")
	}
}

func TestOpenCLInvalidDevice(t *testing.T) {
	p := DefaultOpenCLPlatform()
	if _, err := NewOpenCLBackend(p, 99); err == nil {
		t.Error("expected device index error")
	}
	empty := OpenCLPlatform{Name: "e"}
	if _, err := NewOpenCLBackend(empty, 0); err == nil {
		t.Error("expected platform error")
	}
}

func TestOpenCLOps(t *testing.T) {
	b, _ := NewOpenCLBackend(DefaultOpenCLPlatform(), 0)
	out, err := b.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	if out[0] != 7 {
		t.Errorf("got %v", out)
	}
	sum, _ := b.Add([]float64{1, 1}, []float64{2, 3})
	if sum[0] != 3 {
		t.Error("add")
	}
	x := b.Relu([]float64{-1, 1})
	if x[0] != 0 {
		t.Error("relu")
	}
	if _, err := b.Softmax([]float64{1, 2, 3}, 0); err != nil {
		t.Fatal(err)
	}
	st := b.Stats()
	if st.MatMulOps.Load() != 1 || st.KernelBuilds.Load() != 1 {
		t.Error("stats")
	}
}

func TestBackendTypeStringsAll(t *testing.T) {
	want := map[BackendType]string{
		BackendTypeCPU: "cpu", BackendTypeCUDA: "cuda",
		BackendTypeVulkan: "vulkan", BackendTypeMetal: "metal",
		BackendTypeDirectML: "directml", BackendTypeROCm: "rocm",
		BackendTypeWebGPU: "webgpu", BackendTypeOpenCL: "opencl",
	}
	for bt, s := range want {
		if bt.String() != s {
			t.Errorf("%d: got %s, want %s", bt, bt.String(), s)
		}
	}
}

func TestInitDefaultBackendsIncludesAll(t *testing.T) {
	sel, err := InitDefaultBackends()
	if err != nil {
		t.Fatal(err)
	}
	names := sel.AvailableBackends()
	required := []string{"cpu", "cuda", "vulkan", "metal", "directml", "rocm", "webgpu", "opencl"}
	for _, want := range required {
		found := false
		for _, n := range names {
			if n == want {
				found = true
			}
		}
		if !found {
			t.Errorf("backend %q missing from %v", want, names)
		}
	}
	if sel.Select().Name() != "cpu" {
		t.Error("CPU should be the fallback when no real GPU is present")
	}
}