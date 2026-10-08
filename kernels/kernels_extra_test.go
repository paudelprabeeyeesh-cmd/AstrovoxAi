package kernels

import (
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
)

func TestVecAddZeroLength(t *testing.T) {
	a := view([]int{0}, float64(0))
	b := view([]int{0}, float64(0))
	out := view([]int{0}, float64(0))
	if err := (VecAddKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err != nil {
		t.Fatalf("zero-length: %v", err)
	}
}

func TestVecMulZeroLength(t *testing.T) {
	a := view([]int{0}, float64(0))
	b := view([]int{0}, float64(0))
	out := view([]int{0}, float64(0))
	if err := (VecMulKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err != nil {
		t.Fatalf("zero-length: %v", err)
	}
}

func TestVecAddScalar(t *testing.T) {
	a := view([]int{1}, 3)
	b := view([]int{1}, 7)
	out := view([]int{1}, 0)
	if err := (VecAddKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != 10 {
		t.Fatalf("vec_add = %v, want 10", out.data[0])
	}
}

func TestVecMulScalar(t *testing.T) {
	a := view([]int{1}, 3)
	b := view([]int{1}, 7)
	out := view([]int{1}, 0)
	if err := (VecMulKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != 21 {
		t.Fatalf("vec_mul = %v, want 21", out.data[0])
	}
}

func TestScaleWithZeroScalar(t *testing.T) {
	a := view([]int{3}, 1, 2, 3)
	out := view([]int{3}, 0, 0, 0)
	if err := (ScaleKernel{}).Execute([]TensorView{a}, []TensorView{out}, map[string]any{"scalar": 0.0}); err != nil {
		t.Fatal(err)
	}
	for i, v := range out.data {
		if v != 0 {
			t.Fatalf("out[%d] = %v, want 0", i, v)
		}
	}
}

func TestScaleWithNegativeScalar(t *testing.T) {
	a := view([]int{2}, 1, -2)
	out := view([]int{2}, 0, 0)
	if err := (ScaleKernel{}).Execute([]TensorView{a}, []TensorView{out}, map[string]any{"scalar": -1.0}); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != -1 || out.data[1] != 2 {
		t.Fatalf("scale = %v, want [-1 2]", out.data)
	}
}

func TestReluAllNegative(t *testing.T) {
	a := view([]int{3}, -3, -1, -100)
	out := view([]int{3}, 0, 0, 0)
	if err := (ReluKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	for i, v := range out.data {
		if v != 0 {
			t.Fatalf("out[%d] = %v, want 0", i, v)
		}
	}
}

func TestReluAllPositive(t *testing.T) {
	a := view([]int{3}, 1, 2, 3)
	out := view([]int{3}, 0, 0, 0)
	if err := (ReluKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	for i, v := range out.data {
		if v != a.data[i] {
			t.Fatalf("out[%d] = %v, want %v", i, v, a.data[i])
		}
	}
}

func TestTanhZero(t *testing.T) {
	a := view([]int{1}, 0)
	out := view([]int{1}, 999)
	if err := (TanhKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != 0 {
		t.Fatalf("tanh(0) = %v, want 0", out.data[0])
	}
}

func TestSumEmpty(t *testing.T) {
	a := view([]int{0}, float64(0))
	out := view([]int{1}, 0)
	if err := (SumKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err != nil {
		t.Fatalf("sum empty: %v", err)
	}
	if out.data[0] != 0 {
		t.Fatalf("sum = %v, want 0", out.data[0])
	}
}

func TestSumSingle(t *testing.T) {
	a := view([]int{1}, 42)
	out := view([]int{1}, 0)
	if err := (SumKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != 42 {
		t.Fatalf("sum = %v, want 42", out.data[0])
	}
}

func TestMatMulIdentity(t *testing.T) {
	// 2x2 identity @ 2x2 vector
	a := view([]int{2, 2}, 1, 0, 0, 1)
	b := view([]int{2, 1}, 3, 4)
	out := view([]int{2, 1}, 0, 0)
	if err := (MatMulKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err != nil {
		t.Fatal(err)
	}
	if out.data[0] != 3 || out.data[1] != 4 {
		t.Fatalf("matmul = %v, want [3 4]", out.data)
	}
}

func TestVecAddLengthMismatch(t *testing.T) {
	a := view([]int{2}, 1, 2)
	b := view([]int{3}, 1, 2, 3)
	out := view([]int{2}, 0, 0)
	if err := (VecAddKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err == nil {
		t.Fatal("expected length mismatch error")
	}
}

func TestVecMulLengthMismatch(t *testing.T) {
	a := view([]int{2}, 1, 2)
	b := view([]int{3}, 1, 2, 3)
	out := view([]int{2}, 0, 0)
	if err := (VecMulKernel{}).Execute([]TensorView{a, b}, []TensorView{out}, nil); err == nil {
		t.Fatal("expected length mismatch error")
	}
}

func TestScaleLengthMismatch(t *testing.T) {
	a := view([]int{2}, 1, 2)
	out := view([]int{3}, 0, 0, 0)
	if err := (ScaleKernel{}).Execute([]TensorView{a}, []TensorView{out}, map[string]any{"scalar": 2.0}); err == nil {
		t.Fatal("expected length mismatch error")
	}
}

func TestReluLengthMismatch(t *testing.T) {
	a := view([]int{2}, 1, 2)
	out := view([]int{3}, 0, 0, 0)
	if err := (ReluKernel{}).Execute([]TensorView{a}, []TensorView{out}, nil); err == nil {
		t.Fatal("expected length mismatch error")
	}
}

func TestGPUKernelStubRelu(t *testing.T) {
	k, err := Lookup(backend.DeviceCUDA, "relu")
	if err != nil {
		t.Fatal(err)
	}
	if k.Device() != backend.DeviceCUDA {
		t.Fatalf("device = %v, want cuda", k.Device())
	}
	a := view([]int{2}, -1, 2)
	out := view([]int{2}, 0, 0)
	if err := k.Execute([]TensorView{a}, []TensorView{out}, nil); err == nil {
		t.Fatal("expected unimplemented error")
	}
}

func TestGPUKernelStubTanh(t *testing.T) {
	k, err := Lookup(backend.DeviceCUDA, "tanh")
	if err != nil {
		t.Fatal(err)
	}
	if k.Name() != "tanh" {
		t.Fatalf("name = %q, want tanh", k.Name())
	}
}

func TestGPUStubAllBackends(t *testing.T) {
	for _, dev := range []backend.Device{backend.DeviceCUDA, backend.DeviceROCm, backend.DeviceMetal, backend.DeviceOpenCL} {
		k, err := Lookup(dev, "vec_add")
		if err != nil {
			t.Fatalf("%s: %v", dev, err)
		}
		if k.Device() != dev {
			t.Fatalf("%s device mismatch", dev)
		}
	}
}

func TestListForDeviceROCm(t *testing.T) {
	rocm := ListForDevice(backend.DeviceROCm)
	if len(rocm) != len(GPUKernelNames) {
		t.Fatalf("rocm kernels = %d, want %d", len(rocm), len(GPUKernelNames))
	}
}

func TestKernelRegistryConsistency(t *testing.T) {
	for _, name := range GPUKernelNames {
		for _, dev := range []backend.Device{backend.DeviceCUDA, backend.DeviceROCm, backend.DeviceMetal, backend.DeviceOpenCL} {
			k, err := Lookup(dev, name)
			if err != nil {
				t.Fatalf("%s %s: %v", dev, name, err)
			}
			if k.Name() != name {
				t.Fatalf("%s %s name = %q", dev, name, k.Name())
			}
		}
	}
}
