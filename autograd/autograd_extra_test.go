package autograd

import (
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

func TestNewVariable(t *testing.T) {
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	if v == nil {
		t.Fatal("expected non-nil variable")
	}
}

func TestVariable_RequiresGrad(t *testing.T) {
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	if !v.RequiresGrad() {
		t.Fatal("expected RequiresGrad true")
	}
	v2 := NewVariable(tv, false)
	if v2.RequiresGrad() {
		t.Fatal("expected RequiresGrad false")
	}
}

func TestVariable_ZeroGrad(t *testing.T) {
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	v.ZeroGrad()
	if v.Grad != nil {
		t.Fatal("expected nil grad after ZeroGrad")
	}
}

func TestVariable_Creator(t *testing.T) {
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	if v.Creator {
		t.Fatal("leaf variable should have Creator=false")
	}
}

func TestTape_Record(t *testing.T) {
	tape := NewTape()
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	v.Creator = true
	tape.Record(v)
	if tape.Len() != 1 {
		t.Fatalf("tape len = %d, want 1", tape.Len())
	}
}

func TestTape_Reset(t *testing.T) {
	tape := NewTape()
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	v.Creator = true
	tape.Record(v)
	tape.Reset()
	if tape.Len() != 0 {
		t.Fatalf("tape len = %d, want 0 after reset", tape.Len())
	}
}

func TestTape_MultipleRecords(t *testing.T) {
	tape := NewTape()
	for i := 0; i < 5; i++ {
		tv, _ := tensor.New(tensor.Float64, []int{2})
		v := NewVariable(tv, true)
		v.Creator = true
		tape.Record(v)
	}
	if tape.Len() != 5 {
		t.Fatalf("tape len = %d, want 5", tape.Len())
	}
}

func TestAccumGrad_NoGrad(t *testing.T) {
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, false)
	g, _ := tensor.New(tensor.Float64, []int{2})
	err := v.AccumGrad(g)
	if err != nil {
		t.Fatalf("AccumGrad on no-grad var: %v", err)
	}
	if v.Grad != nil {
		t.Fatal("expected nil grad for no-grad variable")
	}
}

func TestAccumGrad_FirstTime(t *testing.T) {
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	g, _ := tensor.New(tensor.Float64, []int{2})
	err := v.AccumGrad(g)
	if err != nil {
		t.Fatalf("AccumGrad: %v", err)
	}
	if v.Grad == nil {
		t.Fatal("expected grad to be set")
	}
}

func TestSGD_New(t *testing.T) {
	_, err := NewSGD(0.01, 0.9)
	if err != nil {
		t.Fatalf("NewSGD: %v", err)
	}
}

func TestSGD_ZeroGrad(t *testing.T) {
	sgd, _ := NewSGD(0.01, 0.9)
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	sgd.ZeroGrad([]*Variable{v})
	if v.Grad != nil {
		t.Fatal("expected nil grad after ZeroGrad")
	}
}

func TestAdam_New(t *testing.T) {
	_, err := NewAdam(0.001, 0.9, 0.999, 1e-8)
	if err != nil {
		t.Fatalf("NewAdam: %v", err)
	}
}

func TestAdam_ZeroGrad(t *testing.T) {
	adam, _ := NewAdam(0.001, 0.9, 0.999, 1e-8)
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	adam.ZeroGrad([]*Variable{v})
	if v.Grad != nil {
		t.Fatal("expected nil grad after ZeroGrad")
	}
}

func TestVariable_GradAccumulation(t *testing.T) {
	tv, _ := tensor.New(tensor.Float64, []int{2})
	v := NewVariable(tv, true)
	g1, _ := tensor.New(tensor.Float64, []int{2})
	g2, _ := tensor.New(tensor.Float64, []int{2})
	_ = v.AccumGrad(g1)
	_ = v.AccumGrad(g2)
	if v.Grad == nil {
		t.Fatal("expected accumulated grad")
	}
}

func TestTape_EmptyBackward(t *testing.T) {
	tape := NewTape()
	tv, _ := tensor.New(tensor.Float64, []int{2})
	if err := tape.Backward(tv); err != nil {
		t.Fatalf("Backward on empty tape: %v", err)
	}
}
