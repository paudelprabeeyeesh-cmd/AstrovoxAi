package kernels_test

import (
	"testing"

	"github.com/astrovox/astrovox/internal/backend"
	"github.com/astrovox/astrovox/kernels"
)

type floatView struct {
	shape []int
	data  []float64
}

func (f floatView) DType() string { return "float64" }
func (f floatView) Shape() []int  { return f.shape }
func (f floatView) Data() any     { return f.data }

func benchViews(n int) (floatView, floatView, floatView) {
	a := floatView{shape: []int{n}, data: make([]float64, n)}
	b := floatView{shape: []int{n}, data: make([]float64, n)}
	out := floatView{shape: []int{n}, data: make([]float64, n)}
	return a, b, out
}

func BenchmarkVecAddKernel(b *testing.B) {
	a, c, out := benchViews(4096)
	k := kernels.VecAddKernel{}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if err := k.Execute([]kernels.TensorView{a, c}, []kernels.TensorView{out}, nil); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkVecMulKernel(b *testing.B) {
	a, c, out := benchViews(4096)
	k := kernels.VecMulKernel{}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if err := k.Execute([]kernels.TensorView{a, c}, []kernels.TensorView{out}, nil); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkDispatcherRun(b *testing.B) {
	a, c, out := benchViews(4096)
	if err := kernels.Register(kernels.VecAddKernel{}); err != nil {
		b.Fatal(err)
	}
	d := kernels.NewDispatcher(backend.DeviceCPU)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if err := d.Run("vec_add",
			[]kernels.TensorView{a, c},
			[]kernels.TensorView{out}, nil); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkRegisterKernel(b *testing.B) {
	k := kernels.VecAddKernel{}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if err := kernels.Register(k); err != nil {
			b.Fatal(err)
		}
	}
}
