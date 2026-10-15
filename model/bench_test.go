package model_test

import (
	"testing"

	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/internal/checkpoint"
	"github.com/astrovox/astrovox/model"
	"github.com/astrovox/astrovox/tensor"
)

func writeCheckpoint(b *testing.B, path string, cp *checkpoint.FileCheckpoint) error {
	b.Helper()
	return checkpoint.WriteFile(path, cp)
}

func loadCheckpoint(b *testing.B, path string) (*checkpoint.FileCheckpoint, error) {
	b.Helper()
	return checkpoint.ReadFile(path)
}

func benchInput(rows, cols int) *autograd.Variable {
	t, err := tensor.Zeros(tensor.Float64, []int{rows, cols})
	if err != nil {
		panic(err)
	}
	for i := range t.Float64() {
		t.Float64()[i] = float64(i%7) * 0.25
	}
	return autograd.NewVariable(t, false)
}

func BenchmarkLinearForward(b *testing.B) {
	l, err := model.NewLinear("fc", 64, 32, 1)
	if err != nil {
		b.Fatal(err)
	}
	x := benchInput(8, 64)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		out, err := l.Forward(nil, x)
		if err != nil {
			b.Fatal(err)
		}
		_ = out
	}
}

func BenchmarkMLPForward(b *testing.B) {
	m, err := model.NewMLP("mlp", []int{64, 128, 64, 10}, model.ActRelu, 7)
	if err != nil {
		b.Fatal(err)
	}
	x := benchInput(8, 64)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		out, err := m.Forward(nil, x)
		if err != nil {
			b.Fatal(err)
		}
		_ = out
	}
}

func BenchmarkMSELoss(b *testing.B) {
	l, err := model.NewLinear("fc", 32, 8, 3)
	if err != nil {
		b.Fatal(err)
	}
	x := benchInput(16, 32)
	tape := autograd.NewTape()
	pred, err := l.Forward(tape, x)
	if err != nil {
		b.Fatal(err)
	}
	target, err := tensor.Zeros(tensor.Float64, []int{16, 8})
	if err != nil {
		b.Fatal(err)
	}
	tVar := autograd.NewVariable(target, false)
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		loss, err := model.MSELoss(tape, pred, tVar)
		if err != nil {
			b.Fatal(err)
		}
		_ = loss
	}
}

func BenchmarkCheckpointSaveRestore(b *testing.B) {
	m, err := model.NewMLP("mlp", []int{32, 64, 32}, model.ActTanh, 11)
	if err != nil {
		b.Fatal(err)
	}
	cp, err := model.ToCheckpoint("mlp-demo", m)
	if err != nil {
		b.Fatal(err)
	}
	dir := b.TempDir()
	path := dir + "/model.axck"
	b.Run("save", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			if err := writeCheckpoint(b, path, cp); err != nil {
				b.Fatal(err)
			}
		}
	})
	if err := writeCheckpoint(b, path, cp); err != nil {
		b.Fatal(err)
	}
	b.Run("load", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			if _, err := loadCheckpoint(b, path); err != nil {
				b.Fatal(err)
			}
		}
	})
	b.Run("restore", func(b *testing.B) {
		b.ReportAllocs()
		loaded, err := loadCheckpoint(b, path)
		if err != nil {
			b.Fatal(err)
		}
		for i := 0; i < b.N; i++ {
			fresh, err := model.NewMLP("mlp", []int{32, 64, 32}, model.ActTanh, 99)
			if err != nil {
				b.Fatal(err)
			}
			if err := model.RestoreFromCheckpoint(fresh, loaded); err != nil {
				b.Fatal(err)
			}
		}
	})
}
