package backend

import (
	"math"
	"testing"
)

// This file covers the GPU backends: CUDA, Vulkan, Metal, DirectML, ROCm,
// OpenCL and WebGPU, plus the backend selector. Each backend runs on a
// CPU fallback, so results are compared against a shared reference.

func TestCUDACreation(t *testing.T) {
	c, err := NewCUDA(0, 1024)
	if err != nil {
		t.Fatal(err)
	}
	if c.Name() != "cuda" {
		t.Errorf("got %s", c.Name())
	}
	if c.Available() {
		t.Error("no real GPU in CI, so the adapter must report unavailable")
	}
}

func TestCUDADtypes(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	dtypes := c.SupportedDtypes()
	found := false
	for _, d := range dtypes {
		if d == "float16" {
			found = true
		}
	}
	if !found {
		t.Errorf("cuda should support float16, got %v", dtypes)
	}
}

func TestCUDAMatMul(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	out, err := c.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	assertMatrixEqual(t, out, []float64{7, 10, 15, 22})
}

// The tensor-core path requires 8x8-aligned dimensions.
func TestCUDAMatMulTensorCores(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	if !c.HasTensorCores() {
		t.Fatal("expected tensor core support")
	}
	const n = 16
	a := make([]float64, n*n)
	b := make([]float64, n*n)
	for i := range a {
		a[i] = float64(i % 5)
		b[i] = float64((i + 1) % 5)
	}
	out, err := c.MatMul(a, b, n, n, n)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != n*n {
		t.Errorf("expected %d elements, got %d", n*n, len(out))
	}
}

func TestCUDAMemoryPool(t *testing.T) {
	c, _ := NewCUDA(0, 1) // 1 MB
	id, err := c.Allocate(1024)
	if err != nil {
		t.Fatal(err)
	}
	c.Free(id)
	used, _, _ := c.MemoryStats()
	if used != 0 {
		t.Errorf("expected 0 used after free, got %d", used)
	}
}

func TestCUDAMemoryPoolOOM(t *testing.T) {
	c, _ := NewCUDA(0, 1)
	if _, err := c.Allocate(10 * 1024 * 1024); err != ErrCUDAMemory {
		t.Errorf("expected OOM error, got %v", err)
	}
}

func TestCUDAMemoryPoolPeak(t *testing.T) {
	c, _ := NewCUDA(0, 10)
	id1, _ := c.Allocate(1024)
	id2, _ := c.Allocate(2048)
	c.Free(id1)
	c.Free(id2)
	_, peak, _ := c.MemoryStats()
	if peak != 3072 {
		t.Errorf("expected peak 3072, got %d", peak)
	}
}

func TestCUDAStreams(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	s := c.GetStream(0)
	if s.ID() != 0 {
		t.Errorf("expected stream 0, got %d", s.ID())
	}
	if s.Device() != DeviceCUDA {
		t.Error("expected CUDA device")
	}
	if err := s.Synchronize(); err != nil {
		t.Fatal(err)
	}
}

func TestCUDACurrentStream(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	if err := c.SetCurrentStream(2); err != nil {
		t.Fatal(err)
	}
	if c.CurrentStream().ID() != 2 {
		t.Error("current stream should be 2")
	}
	if err := c.SetCurrentStream(99); err == nil {
		t.Error("expected error for an invalid stream index")
	}
}

func TestCUDAElementwiseOps(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	add, err := c.Add([]float64{1, 2, 3}, []float64{4, 5, 6})
	if err != nil {
		t.Fatal(err)
	}
	want := []float64{5, 7, 9}
	for i := range want {
		if add[i] != want[i] {
			t.Errorf("element %d = %v, want %v", i, add[i], want[i])
		}
	}

	x := c.Relu([]float64{-1, 0, 1})
	if x[0] != 0 || x[1] != 0 || x[2] != 1 {
		t.Errorf("relu: %v", x)
	}

	sm, err := c.Softmax([]float64{1, 2, 3}, 0)
	if err != nil {
		t.Fatal(err)
	}
	if sum := total(sm); math.Abs(sum-1) > 1e-9 {
		t.Errorf("softmax sum = %v", sum)
	}
}

func TestCUDAStats(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	c.MatMul(make([]float64, 4), make([]float64, 4), 2, 2, 2)
	if c.stats.MatMulOps.Load() != 1 {
		t.Errorf("expected 1 matmul, got %d", c.stats.MatMulOps.Load())
	}
	if c.stats.KernelLaunches.Load() != 1 {
		t.Errorf("expected 1 launch, got %d", c.stats.KernelLaunches.Load())
	}
}

func TestCUDACapabilities(t *testing.T) {
	c, _ := NewCUDA(0, 2048)
	caps := c.Capabilities()
	if len(caps.Dtypes) == 0 {
		t.Error("expected dtypes")
	}
	if caps.MaxMemory != 2048*1024*1024 {
		t.Errorf("expected 2048MB, got %d", caps.MaxMemory)
	}
	if !caps.HasStreams {
		t.Error("expected stream support")
	}
}

func TestCUDAEvent(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	s := c.GetStream(0)
	e := &CUDAEvent{}
	if err := e.Record(s); err != nil {
		t.Fatal(err)
	}
	if !e.IsComplete() {
		t.Error("event should be complete")
	}
}

func TestCUDAKernelLaunch(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	launcher := NewCUDAKernelLauncher(c)
	launched := 0
	kernel := &CUDAKernel{
		Name: "test",
		Fn:   func(args ...interface{}) error { launched++; return nil },
	}
	if err := launcher.Launch(kernel); err != nil {
		t.Fatal(err)
	}
	if launched != 1 {
		t.Errorf("expected 1 invocation, got %d", launched)
	}
	if err := launcher.Launch(&CUDAKernel{Name: "no-fn"}); err == nil {
		t.Error("expected an error for a kernel with no function")
	}
}

func TestCUDAKernelLaunchConfig(t *testing.T) {
	kernel := &CUDAKernel{
		Name:      "test",
		GridDimX:  10,
		BlockDimX: 256,
		SharedMem: 1024,
	}
	if kernel.LaunchConfig() == "" {
		t.Error("expected a non-empty launch config")
	}
}

func TestCUDAGraph(t *testing.T) {
	c, _ := NewCUDA(0, 1024)
	g := NewCUDAGraph()
	launcher := NewCUDAKernelLauncher(c)
	invocations := 0
	mk := func() *CUDAKernel {
		return &CUDAKernel{Fn: func(args ...interface{}) error { invocations++; return nil }}
	}

	g.BeginCapture()
	g.AddOp(mk())
	g.AddOp(mk())
	g.EndCapture()

	if err := g.Replay(launcher); err != nil {
		t.Fatal(err)
	}
	if invocations != 2 {
		t.Errorf("expected 2 kernel invocations on replay, got %d", invocations)
	}
	if g.instantiations.Load() != 1 {
		t.Error("graph should be replayed once")
	}
}

// ---------------------------------------------------------------------------
// Vulkan
// ---------------------------------------------------------------------------

func TestVulkanCreation(t *testing.T) {
	v, err := NewVulkan(VulkanDeviceTypeDiscreteGPU, 4096)
	if err != nil {
		t.Fatal(err)
	}
	if v.Name() != "vulkan" {
		t.Errorf("got %s", v.Name())
	}
	if v.Available() {
		t.Error("no real GPU in CI, so the device must report unavailable")
	}
}

func TestVulkanDeviceQueues(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	if len(v.device.computeQueues) == 0 {
		t.Error("expected compute queues")
	}
	if len(v.device.graphicsQueues) == 0 {
		t.Error("expected graphics queues")
	}
	if len(v.device.transferQueues) == 0 {
		t.Error("expected transfer queues")
	}
}

func TestVulkanMatMul(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	out, err := v.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	assertMatrixEqual(t, out, []float64{7, 10, 15, 22})
}

func TestVulkanPipeline(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	p, err := v.CreatePipeline("test", []byte("shader"))
	if err != nil {
		t.Fatal(err)
	}
	if !p.IsCompiled() {
		t.Error("pipeline should be compiled")
	}
	if p.ExecutionCount() != 0 {
		t.Error("pipeline should not be executed yet")
	}
}

func TestVulkanPipelineEmptyShader(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	if _, err := v.CreatePipeline("bad", nil); err != ErrVulkanPipeline {
		t.Errorf("expected pipeline error, got %v", err)
	}
}

func TestVulkanCommandBuffer(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	cb := v.GetStream(0).cmdBuffer
	if err := cb.Begin(); err != nil {
		t.Fatal(err)
	}
	if cb.state != VulkanCommandBufferStateRecording {
		t.Error("expected the recording state")
	}
	if err := cb.End(); err != nil {
		t.Fatal(err)
	}
}

func TestVulkanDispatch(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	p, _ := v.CreatePipeline("test", []byte("shader"))
	stream := v.GetStream(0)
	if err := v.Dispatch(stream, p, 10, 10, 1, nil); err != nil {
		t.Fatal(err)
	}
	if p.ExecutionCount() != 1 {
		t.Error("pipeline should be executed once")
	}
	if err := v.Dispatch(stream, nil, 1, 1, 1, nil); err != ErrVulkanPipeline {
		t.Errorf("expected pipeline error for a nil pipeline, got %v", err)
	}
}

func TestVulkanMemoryAllocation(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	offset, err := v.Allocate(4096, true)
	if err != nil {
		t.Fatal(err)
	}
	if offset != 0 {
		t.Errorf("expected offset 0 for the first allocation, got %d", offset)
	}
}

func TestVulkanSoftmax(t *testing.T) {
	v, _ := NewVulkan(VulkanDeviceTypeDiscreteGPU, 1024)
	out, err := v.Softmax([]float64{1, 2, 3}, 0)
	if err != nil {
		t.Fatal(err)
	}
	if sum := total(out); math.Abs(sum-1) > 1e-9 {
		t.Errorf("softmax sum = %v", sum)
	}
}

func TestVulkanSPIRVCompiler(t *testing.T) {
	c := NewVulkanSPIRVCompiler()
	spirv, err := c.CompileGLSL("#version 450\nvoid main() {}")
	if err != nil {
		t.Fatal(err)
	}
	if len(spirv) == 0 {
		t.Error("expected SPIR-V output")
	}
}

// ---------------------------------------------------------------------------
// Metal
// ---------------------------------------------------------------------------

func TestMetalCreation(t *testing.T) {
	m, err := NewMetal(1024)
	if err != nil {
		t.Fatal(err)
	}
	if m.Name() != "metal" {
		t.Errorf("got %s", m.Name())
	}
}

func TestMetalUnifiedMemory(t *testing.T) {
	m, _ := NewMetal(1024)
	if !m.device.hasUnifiedMemory {
		t.Error("Metal should have unified memory")
	}
}

func TestMetalBuffer(t *testing.T) {
	m, _ := NewMetal(1024)
	buf, err := m.CreateBuffer(1024)
	if err != nil {
		t.Fatal(err)
	}
	data := []byte{1, 2, 3, 4}
	if err := m.WriteBuffer(buf, data); err != nil {
		t.Fatal(err)
	}
	read, err := m.ReadBuffer(buf)
	if err != nil {
		t.Fatal(err)
	}
	for i, b := range data {
		if read[i] != b {
			t.Errorf("byte %d: got %d, want %d", i, read[i], b)
		}
	}
	m.ReleaseBuffer(buf)
	if err := m.WriteBuffer(buf, data); err == nil {
		t.Error("expected an error writing to a released buffer")
	}
}

func TestMetalBufferTooLarge(t *testing.T) {
	m, _ := NewMetal(1) // 1 MB
	if _, err := m.CreateBuffer(10 * 1024 * 1024); err != ErrMetalBuffer {
		t.Errorf("expected buffer error, got %v", err)
	}
}

func TestMetalPipeline(t *testing.T) {
	m, _ := NewMetal(1024)
	p, err := m.CreatePipeline("test", "main", "kernel void main() {}")
	if err != nil {
		t.Fatal(err)
	}
	if !p.IsCompiled() {
		t.Error("pipeline should be compiled")
	}
	if _, err := m.CreatePipeline("bad", "main", ""); err == nil {
		t.Error("expected an error for empty shader source")
	}
}

func TestMetalCommandBuffer(t *testing.T) {
	m, _ := NewMetal(1024)
	p, _ := m.CreatePipeline("test", "main", "kernel void main() {}")
	q := m.GetQueue(0)
	cb := m.CreateCommandBuffer(q)
	enc, err := m.CreateComputeEncoder(cb, p)
	if err != nil {
		t.Fatal(err)
	}
	if err := enc.DispatchThreadgroups(10, 64); err != nil {
		t.Fatal(err)
	}
	enc.EndEncoding()
	cb.Commit()
	cb.WaitUntilCompleted()
	if p.execCount.Load() != 1 {
		t.Errorf("pipeline should be executed once, got %d", p.execCount.Load())
	}
}

func TestMetalMatMul(t *testing.T) {
	m, _ := NewMetal(1024)
	out, err := m.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	assertMatrixEqual(t, out, []float64{7, 10, 15, 22})
}

func TestMetalStats(t *testing.T) {
	m, _ := NewMetal(1024)
	m.MatMul(make([]float64, 4), make([]float64, 4), 2, 2, 2)
	if m.stats.MatMulOps.Load() != 1 {
		t.Errorf("expected 1 matmul, got %d", m.stats.MatMulOps.Load())
	}
}

// ---------------------------------------------------------------------------
// DirectML
// ---------------------------------------------------------------------------

func TestDirectMLCreation(t *testing.T) {
	d, err := NewDirectML(0)
	if err != nil {
		t.Fatal(err)
	}
	if d.Name() != "directml" {
		t.Errorf("got %s", d.Name())
	}
	if d.Available() {
		t.Error("no real GPU in CI, so the device must report unavailable")
	}
}

func TestDirectMLMatMul(t *testing.T) {
	d, _ := NewDirectML(0)
	out, err := d.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	assertMatrixEqual(t, out, []float64{7, 10, 15, 22})
}

func TestDirectMLSoftmax(t *testing.T) {
	d, _ := NewDirectML(0)
	out, err := d.Softmax([]float64{1, 2, 3}, 0)
	if err != nil {
		t.Fatal(err)
	}
	if sum := total(out); math.Abs(sum-1) > 1e-9 {
		t.Errorf("softmax sum = %v", sum)
	}
}

// ---------------------------------------------------------------------------
// ROCm
// ---------------------------------------------------------------------------

func TestROCmCreation(t *testing.T) {
	r, err := NewROCmBackend(0)
	if err != nil {
		t.Fatal(err)
	}
	if r.Name() != "rocm" || r.GCNArch() != "gfx90a" {
		t.Error("rocm setup")
	}
	if r.Available() {
		t.Error("no AMD GPU in CI, so the device must report unavailable")
	}
	if _, err := NewROCmBackend(-1); err == nil {
		t.Error("expected a device index error")
	}
}

func TestROCmMatMul(t *testing.T) {
	r, _ := NewROCmBackend(0)
	out, _ := r.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	assertMatrixEqual(t, out, []float64{7, 10, 15, 22})
}

func TestROCmElementwiseOps(t *testing.T) {
	r, _ := NewROCmBackend(0)
	if _, err := r.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2); err != nil {
		t.Fatal(err)
	}
	add, err := r.Add([]float64{1}, []float64{2})
	if err != nil {
		t.Fatal(err)
	}
	if add[0] != 3 {
		t.Errorf("got %v", add)
	}
	if _, err := r.Add([]float64{1, 2}, []float64{3}); err == nil {
		t.Error("expected a shape mismatch error")
	}
	x := r.Relu([]float64{-2, 3})
	if x[0] != 0 || x[1] != 3 {
		t.Errorf("relu: %v", x)
	}
	if _, err := r.Softmax([]float64{1, 2}, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := r.Softmax(nil, 0); err == nil {
		t.Error("expected an error for empty input")
	}
	st := r.Stats()
	if st.MatMulOps.Load() < 1 || st.KernelLaunches.Load() < 1 {
		t.Errorf("expected matmul statistics, got %d/%d", st.MatMulOps.Load(), st.KernelLaunches.Load())
	}
	if _, err := r.MatMul([]float64{1}, []float64{1, 2}, 2, 2, 2); err == nil {
		t.Error("expected a dimension error")
	}
}

// ---------------------------------------------------------------------------
// OpenCL
// ---------------------------------------------------------------------------

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
		t.Errorf("got %s", b.Name())
	}
	// BestDevice should pick the GPU (80 units × 1800 MHz beats 16 × 3200).
	if got := b.BestDevice().Name; got != "Sim GPU" {
		t.Errorf("expected Sim GPU, got %s", got)
	}
	if OpenCLDeviceTypeCPU.String() != "cpu" || OpenCLDeviceTypeGPU.String() != "gpu" {
		t.Error("device type strings")
	}
}

func TestOpenCLInvalidDevice(t *testing.T) {
	p := DefaultOpenCLPlatform()
	if _, err := NewOpenCLBackend(p, 99); err == nil {
		t.Error("expected a device index error")
	}
	if _, err := NewOpenCLBackend(OpenCLPlatform{Name: "e"}, 0); err == nil {
		t.Error("expected a platform error")
	}
}

func TestOpenCLMatMul(t *testing.T) {
	b, _ := NewOpenCLBackend(DefaultOpenCLPlatform(), 0)
	out, err := b.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	assertMatrixEqual(t, out, []float64{7, 10, 15, 22})
}

func TestOpenCLElementwiseOps(t *testing.T) {
	b, _ := NewOpenCLBackend(DefaultOpenCLPlatform(), 0)
	if _, err := b.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2); err != nil {
		t.Fatal(err)
	}
	add, _ := b.Add([]float64{1, 1}, []float64{2, 3})
	if add[0] != 3 {
		t.Errorf("got %v", add)
	}
	if _, err := b.Add([]float64{1}, []float64{1, 2}); err == nil {
		t.Error("expected a shape mismatch error")
	}
	x := b.Relu([]float64{-1, 1})
	if x[0] != 0 {
		t.Errorf("relu: %v", x)
	}
	if _, err := b.Softmax([]float64{1, 2, 3}, 0); err != nil {
		t.Fatal(err)
	}
	if _, err := b.Softmax(nil, 0); err == nil {
		t.Error("expected an error for empty input")
	}
	st := b.Stats()
	if st.MatMulOps.Load() < 1 || st.KernelBuilds.Load() < 1 {
		t.Errorf("expected matmul statistics, got %d/%d", st.MatMulOps.Load(), st.KernelBuilds.Load())
	}
}

// ---------------------------------------------------------------------------
// WebGPU
// ---------------------------------------------------------------------------

func TestWebGPUCreation(t *testing.T) {
	w, err := NewWebGPU(DefaultWebGPUAdapter())
	if err != nil {
		t.Fatal(err)
	}
	if w.Name() != "webgpu" {
		t.Errorf("got %s", w.Name())
	}
	if w.Available() {
		t.Error("no real GPU in CI, so the adapter must report unavailable")
	}
	if w.Adapter().String() == "" {
		t.Error("expected a non-empty adapter summary")
	}
}

func TestWebGPUInvalidAdapter(t *testing.T) {
	if _, err := NewWebGPU(WebGPUAdapter{}); err == nil {
		t.Error("expected an error for an empty adapter")
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
		t.Error("expected the buffer to be released")
	}
	w.DestroyBuffer(nil) // must not panic
}

func TestWebGPUBufferLimits(t *testing.T) {
	w, _ := NewWebGPU(DefaultWebGPUAdapter())
	if _, err := w.CreateBuffer("x", 0, WebGPUBufferUsageStorage); err == nil {
		t.Error("expected a zero-size error")
	}
	// Use the adapter's own limit to prove the bound is enforced.
	huge := uint64(w.adapter.Limits.maxBufferSize) + 1
	if _, err := w.CreateBuffer("big", huge, WebGPUBufferUsageStorage); err != ErrWebGPUBufferSize {
		t.Errorf("expected a size error, got %v", err)
	}
}

func TestWebGPUPipelines(t *testing.T) {
	w, _ := NewWebGPU(DefaultWebGPUAdapter())
	p, err := w.CreatePipeline("matmul", "main", 64, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	if !p.compiled.Load() {
		t.Error("pipeline should be compiled")
	}
	if err := w.Dispatch(p, 16, 1, 1); err != nil {
		t.Fatal(err)
	}
	// An oversized workgroup dimension must be rejected.
	if _, err := w.CreatePipeline("bad", "main", 99999, 1, 1); err == nil {
		t.Error("expected a workgroup limit error")
	}
	// Too many invocations per workgroup must be rejected.
	if _, err := w.CreatePipeline("bad2", "main", 256, 256, 1); err == nil {
		t.Error("expected an invocation limit error")
	}
	if err := w.Dispatch(nil, 1, 1, 1); err != ErrWebGPUPipeline {
		t.Errorf("expected a pipeline error, got %v", err)
	}
}

func TestWebGPUOps(t *testing.T) {
	w, _ := NewWebGPU(DefaultWebGPUAdapter())
	out, err := w.MatMul([]float64{1, 2, 3, 4}, []float64{1, 2, 3, 4}, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	assertMatrixEqual(t, out, []float64{7, 10, 15, 22})

	sum, err := w.Add([]float64{1, 2}, []float64{3, 4})
	if err != nil {
		t.Fatal(err)
	}
	if sum[0] != 4 {
		t.Errorf("got %v", sum)
	}

	x := w.Relu([]float64{-1, 2})
	if x[0] != 0 {
		t.Errorf("relu: %v", x)
	}

	sm, err := w.Softmax([]float64{1, 2, 3}, 0)
	if err != nil {
		t.Fatal(err)
	}
	if sum := total(sm); math.Abs(sum-1) > 1e-9 {
		t.Errorf("softmax sum = %v", sum)
	}
	if _, err := w.Softmax(nil, 0); err == nil {
		t.Error("expected an error for empty input")
	}
}

// ---------------------------------------------------------------------------
// Cross-backend parity
// ---------------------------------------------------------------------------

// allBackends returns every backend so parity tests cover them uniformly.
func allBackends(t *testing.T) []Backend {
	t.Helper()
	backends := []Backend{NewCPUBackend()}
	if c, err := NewCUDA(0, 64); err == nil {
		backends = append(backends, c)
	}
	if v, err := NewVulkan(VulkanDeviceTypeDiscreteGPU, 64); err == nil {
		backends = append(backends, v)
	}
	if m, err := NewMetal(64); err == nil {
		backends = append(backends, m)
	}
	if d, err := NewDirectML(0); err == nil {
		backends = append(backends, d)
	}
	if r, err := NewROCmBackend(0); err == nil {
		backends = append(backends, r)
	}
	if w, err := NewWebGPU(DefaultWebGPUAdapter()); err == nil {
		backends = append(backends, w)
	}
	if o, err := NewOpenCLBackend(DefaultOpenCLPlatform(), 0); err == nil {
		backends = append(backends, o)
	}
	return backends
}

// TestBackendParity verifies every backend computes identical results for
// MatMul, Add, Relu and Softmax.
func TestBackendParity(t *testing.T) {
	backends := allBackends(t)
	if len(backends) < 4 {
		t.Fatalf("expected at least 4 backends, got %d", len(backends))
	}

	a := []float64{1, 2, 3, 4}
	b := []float64{5, 6, 7, 8}
	wantMatMul := []float64{19, 22, 43, 50}
	wantAdd := []float64{6, 8, 10, 12}
	wantRelu := []float64{0, 2}
	wantSoftmax, err := backends[0].Softmax([]float64{1, 2, 3}, 0)
	if err != nil {
		t.Fatal(err)
	}

	for _, bk := range backends {
		out, err := bk.MatMul(a, b, 2, 2, 2)
		if err != nil {
			t.Errorf("%s matmul: %v", bk.Name(), err)
			continue
		}
		if !equalSlices(out, wantMatMul) {
			t.Errorf("%s matmul = %v, want %v", bk.Name(), out, wantMatMul)
		}

		add, err := bk.Add(a, b)
		if err != nil {
			t.Errorf("%s add: %v", bk.Name(), err)
			continue
		}
		if !equalSlices(add, wantAdd) {
			t.Errorf("%s add = %v, want %v", bk.Name(), add, wantAdd)
		}

		if relu := bk.Relu([]float64{-1, 2}); !equalSlices(relu, wantRelu) {
			t.Errorf("%s relu = %v, want %v", bk.Name(), relu, wantRelu)
		}

		soft, err := bk.Softmax([]float64{1, 2, 3}, 0)
		if err != nil {
			t.Errorf("%s softmax: %v", bk.Name(), err)
			continue
		}
		for i := range wantSoftmax {
			if d := soft[i] - wantSoftmax[i]; d > 1e-12 || d < -1e-12 {
				t.Errorf("%s softmax[%d] = %v, want %v", bk.Name(), i, soft[i], wantSoftmax[i])
			}
		}
	}
}

// ---------------------------------------------------------------------------
// Selector
// ---------------------------------------------------------------------------

func TestBackendSelectorCPUFallback(t *testing.T) {
	cpu := NewCPUBackend()
	selector := NewBackendSelector(BackendTypeCUDA, cpu)
	selector.Register(cpu)
	// No real GPU is present, so CPU must be the fallback.
	if selected := selector.Select(); selected.Name() != "cpu" {
		t.Errorf("expected cpu, got %q", selected.Name())
	}
}

func TestBackendSelectorGet(t *testing.T) {
	cpu := NewCPUBackend()
	selector := NewBackendSelector(BackendTypeCUDA, cpu)
	selector.Register(cpu)
	b, ok := selector.Get("cpu")
	if !ok || b.Name() != "cpu" {
		t.Error("expected to find the cpu backend")
	}
	if _, ok := selector.Get("nope"); ok {
		t.Error("expected no such backend")
	}
	if len(selector.AvailableBackends()) != 1 {
		t.Errorf("expected 1 backend, got %v", selector.AvailableBackends())
	}
}

func TestInitDefaultBackendsIncludesAll(t *testing.T) {
	selector, err := InitDefaultBackends()
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"cpu", "cuda", "vulkan", "metal", "directml", "rocm", "webgpu", "opencl"}
	available := selector.AvailableBackends()
	for _, name := range want {
		found := false
		for _, have := range available {
			if have == name {
				found = true
			}
		}
		if !found {
			t.Errorf("backend %q missing from %v", name, available)
		}
	}
	// CPU is the fallback when no real GPU is present.
	if selected := selector.Select(); selected.Name() != "cpu" {
		t.Errorf("expected cpu fallback, got %q", selected.Name())
	}
	// Discovered backends must be visible through the global registry too.
	for _, name := range want {
		if _, ok := GetBackend(name); !ok {
			t.Errorf("global registry is missing %q", name)
		}
	}
}

func TestBackendTypeStrings(t *testing.T) {
	want := map[BackendType]string{
		BackendTypeCPU:      "cpu",
		BackendTypeCUDA:     "cuda",
		BackendTypeVulkan:   "vulkan",
		BackendTypeMetal:    "metal",
		BackendTypeDirectML: "directml",
		BackendTypeROCm:     "rocm",
		BackendTypeWebGPU:   "webgpu",
		BackendTypeOpenCL:   "opencl",
	}
	for bt, s := range want {
		if got := bt.String(); got != s {
			t.Errorf("BackendType(%d) = %q, want %q", bt, got, s)
		}
	}
	if BackendType(99).String() != "unknown" {
		t.Error("expected unknown")
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func assertMatrixEqual(t *testing.T, got, want []float64) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("length mismatch: got %d, want %d", len(got), len(want))
	}
	for i := range want {
		if d := got[i] - want[i]; d > 1e-9 || d < -1e-9 {
			t.Errorf("element %d: got %v, want %v", i, got[i], want[i])
		}
	}
}

func equalSlices(a, b []float64) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func total(xs []float64) float64 {
	sum := 0.0
	for _, x := range xs {
		sum += x
	}
	return sum
}

// mathExp is re-exported here only for the package-internal tests that
// exercise the softmax helpers; the implementation lives in metal_directml.go.

var _ = math.Exp
