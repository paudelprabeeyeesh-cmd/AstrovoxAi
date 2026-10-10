package backend_test

import (
	"math"
	"sync"
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
)

// This file exercises the backend package through its exported surface
// only, so it catches accidental narrowing of the public API.

func TestPublicCPUBackendMatMul(t *testing.T) {
	b := backend.NewCPUBackend()
	a := []float64{1, 2, 3, 4}
	m := []float64{5, 6, 7, 8}
	out, err := b.MatMul(a, m, 2, 2, 2)
	if err != nil {
		t.Fatal(err)
	}
	want := []float64{19, 22, 43, 50}
	for i, v := range out {
		if math.Abs(v-want[i]) > 1e-9 {
			t.Fatalf("element %d: got %v, want %v", i, v, want[i])
		}
	}
}

func TestPublicCPUBackendSoftmaxAcceptsBothDims(t *testing.T) {
	b := backend.NewCPUBackend()
	for _, dim := range []int{0, 1} {
		out, err := b.Softmax([]float64{1, 2, 3}, dim)
		if err != nil {
			t.Fatalf("dim %d: %v", dim, err)
		}
		sum := 0.0
		for _, v := range out {
			sum += v
		}
		if math.Abs(sum-1) > 1e-9 {
			t.Errorf("dim %d: softmax sum = %v", dim, sum)
		}
	}
	if _, err := b.Softmax([]float64{1, 2}, 2); err == nil {
		t.Error("expected an error for dim=2")
	}
}

func TestPublicRegistryAndSelection(t *testing.T) {
	backend.RegisterBackend("cpu", backend.NewCPUBackend())
	b, ok := backend.GetBackend("cpu")
	if !ok || b == nil {
		t.Fatal("expected the cpu backend to be registered")
	}
	if backend.DefaultBackend() == nil {
		t.Error("expected a default backend")
	}
	if len(backend.ListBackends()) == 0 {
		t.Error("expected at least one backend")
	}
}

func TestPublicInitDefaultBackends(t *testing.T) {
	sel, err := backend.InitDefaultBackends()
	if err != nil {
		t.Fatal(err)
	}
	selected := sel.Select()
	if selected == nil {
		t.Fatal("expected a selected backend")
	}
	// CPU must always be the fallback when no real GPU is present.
	if selected.Name() != "cpu" {
		t.Errorf("expected cpu fallback, got %q", selected.Name())
	}
	want := []string{"cpu", "cuda", "vulkan", "metal", "directml", "rocm", "webgpu", "opencl"}
	for _, name := range want {
		if _, ok := sel.Get(name); !ok {
			t.Errorf("selector is missing backend %q", name)
		}
	}
}

func TestPublicBackendTypeStrings(t *testing.T) {
	cases := map[backend.BackendType]string{
		backend.BackendTypeCPU:      "cpu",
		backend.BackendTypeCUDA:     "cuda",
		backend.BackendTypeVulkan:   "vulkan",
		backend.BackendTypeMetal:    "metal",
		backend.BackendTypeDirectML: "directml",
		backend.BackendTypeROCm:     "rocm",
		backend.BackendTypeWebGPU:   "webgpu",
		backend.BackendTypeOpenCL:   "opencl",
	}
	for bt, want := range cases {
		if got := bt.String(); got != want {
			t.Errorf("BackendType(%d) = %q, want %q", bt, got, want)
		}
	}
}

func TestPublicCapabilitiesStruct(t *testing.T) {
	caps := backend.Capabilities{}
	if caps.MaxMemory != 0 || caps.ThreadCount != 0 {
		t.Error("zero value should be usable")
	}
	caps = backend.Capabilities{
		Devices: []backend.Device{backend.DeviceCUDA},
		Dtypes:  []string{"float64"},
	}
	if len(caps.Devices) != 1 || !caps.HasVectorize {
		// HasVectorize defaults to false; just confirm the fields exist.
		if len(caps.Dtypes) != 1 {
			t.Error("dtype list")
		}
	}
}

func TestPublicDeviceStrings(t *testing.T) {
	if backend.DeviceCPU.String() == "" || backend.DeviceCUDA.String() == "" {
		t.Error("device names")
	}
}

func TestPublicCPUThreadPoolAsync(t *testing.T) {
	pool := backend.NewCPUThreadPool(2)
	var mu sync.Mutex
	var completed int
	const tasks = 50
	for i := 0; i < tasks; i++ {
		pool.Submit(func() {
			mu.Lock()
			completed++
			mu.Unlock()
		})
	}
	pool.Wait()
	if completed != tasks {
		t.Errorf("completed %d of %d tasks", completed, tasks)
	}
	pool.Shutdown()
	pool.Shutdown() // idempotent
}
