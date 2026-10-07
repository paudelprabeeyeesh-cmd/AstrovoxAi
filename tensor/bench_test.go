package tensor_test

import (
	"testing"

	"github.com/astrovox/astrovox/tensor"
	"github.com/astrovox/astrovox/tensor/ops"
)

func BenchmarkTensorNew(b *testing.B) {
	for i := 0; i < b.N; i++ {
		if _, err := tensor.New(tensor.Float32, []int{256, 256}); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkTensorZeros(b *testing.B) {
	for i := 0; i < b.N; i++ {
		if _, err := tensor.Zeros(tensor.Float64, []int{128, 128}); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkTensorFill(b *testing.B) {
	t, err := tensor.New(tensor.Float32, []int{256, 256})
	if err != nil {
		b.Fatal(err)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := tensor.Fill(t, 1.5); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkOpsAdd(b *testing.B) {
	a, err := tensor.Ones(tensor.Float64, []int{512, 512})
	if err != nil {
		b.Fatal(err)
	}
	c, err := tensor.Ones(tensor.Float64, []int{512, 512})
	if err != nil {
		b.Fatal(err)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := ops.Add(a, c); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkOpsMatMul(b *testing.B) {
	a, err := tensor.Ones(tensor.Float64, []int{128, 128})
	if err != nil {
		b.Fatal(err)
	}
	c, err := tensor.Ones(tensor.Float64, []int{128, 128})
	if err != nil {
		b.Fatal(err)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := ops.MatMul(a, c); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkOpsBroadcastAdd(b *testing.B) {
	a, err := tensor.Ones(tensor.Float64, []int{512, 512})
	if err != nil {
		b.Fatal(err)
	}
	c, err := tensor.Ones(tensor.Float64, []int{512})
	if err != nil {
		b.Fatal(err)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := ops.Add(a, c); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkTensorReshape(b *testing.B) {
	a, err := tensor.New(tensor.Float32, []int{512, 512})
	if err != nil {
		b.Fatal(err)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := a.Reshape(262144); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkTensorTranspose(b *testing.B) {
	a, err := tensor.New(tensor.Float32, []int{256, 256})
	if err != nil {
		b.Fatal(err)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := a.Transpose(0, 1); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkTensorSerialize(b *testing.B) {
	a, err := tensor.Ones(tensor.Float32, []int{256, 256})
	if err != nil {
		b.Fatal(err)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := tensor.Save(a); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkTensorRoundTrip(b *testing.B) {
	a, err := tensor.Ones(tensor.Float32, []int{256, 256})
	if err != nil {
		b.Fatal(err)
	}
	data, err := tensor.Save(a)
	if err != nil {
		b.Fatal(err)
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := tensor.Load(data); err != nil {
			b.Fatal(err)
		}
	}
}
