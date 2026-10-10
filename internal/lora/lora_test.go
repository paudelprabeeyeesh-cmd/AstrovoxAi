package lora

import (
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

func mkWeight(out, in int) *tensor.Tensor {
	w, _ := tensor.New(tensor.Float64, []int{out, in})
	return w
}

func TestDefaultLoRAConfig(t *testing.T) {
	c := DefaultLoRAConfig()
	if c.Rank != 8 || c.Alpha != 16 {
		t.Errorf("got %+v", c)
	}
	if c.Scaling() != 2.0 {
		t.Errorf("expected scaling 2.0, got %f", c.Scaling())
	}
}

func TestScalingZeroRank(t *testing.T) {
	if (LoRAConfig{Rank: 0}).Scaling() != 0 {
		t.Error("zero rank should give zero scaling")
	}
}

func TestNewLoRALayer(t *testing.T) {
	l, err := NewLoRALayer("fc", 4, 6, LoRAConfig{Rank: 2, Alpha: 4})
	if err != nil {
		t.Fatal(err)
	}
	if l.InDim != 4 || l.OutDim != 6 {
		t.Error("dims")
	}
	if l.ParamCount() != 2*(4+6) {
		t.Errorf("expected 20 params, got %d", l.ParamCount())
	}
	if !l.IsEnabled() {
		t.Error("expected enabled by default")
	}
}

func TestNewLoRALayerInvalid(t *testing.T) {
	if _, err := NewLoRALayer("x", 4, 6, LoRAConfig{Rank: 0}); err == nil {
		t.Error("expected rank error")
	}
	if _, err := NewLoRALayer("x", 0, 6, LoRAConfig{Rank: 2}); err == nil {
		t.Error("expected dim error")
	}
}

func TestMergeIntoZeroDelta(t *testing.T) {
	// B is zero-initialised, so the delta must be zero.
	w := mkWeight(6, 4)
	before := append([]float64(nil), w.Float64()...)
	l, _ := NewLoRALayer("fc", 4, 6, LoRAConfig{Rank: 2, Alpha: 4})
	if err := l.MergeInto(w); err != nil {
		t.Fatal(err)
	}
	for i := range before {
		if w.Float64()[i] != before[i] {
			t.Fatal("zero-B must leave the base weight unchanged")
		}
	}
}

func TestMergeIntoNonZeroDelta(t *testing.T) {
	w := mkWeight(2, 2)
	l, _ := NewLoRALayer("fc", 2, 2, LoRAConfig{Rank: 1, Alpha: 1}) // scaling 1
	// B=1, A=1 => delta = [[1,1],[1,1]]
	l.B.Float64()[0] = 1
	l.B.Float64()[1] = 1
	l.A.Float64()[0] = 1
	l.A.Float64()[1] = 1
	if err := l.MergeInto(w); err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 4; i++ {
		if w.Float64()[i] != 1 {
			t.Errorf("element %d: expected 1, got %f", i, w.Float64()[i])
		}
	}
}

func TestMergeIntoShapeMismatch(t *testing.T) {
	l, _ := NewLoRALayer("fc", 4, 6, LoRAConfig{Rank: 2})
	if err := l.MergeInto(mkWeight(6, 5)); err == nil {
		t.Error("expected shape mismatch error")
	}
	if l.MergeInto(nil) == nil {
		t.Error("expected nil base error")
	}
}

func TestSetEnabled(t *testing.T) {
	l, _ := NewLoRALayer("fc", 4, 4, LoRAConfig{Rank: 2})
	l.SetEnabled(false)
	if l.IsEnabled() {
		t.Error("expected disabled")
	}
}

func TestLoRAModel(t *testing.T) {
	m := NewLoRAModel(LoRAConfig{Rank: 4, Alpha: 8})
	if err := m.AddBase("layer0.fc", mkWeight(8, 4)); err != nil {
		t.Fatal(err)
	}
	if len(m.Layers()) != 1 {
		t.Errorf("expected 1 adapter, got %v", m.Layers())
	}
	if m.TrainableParams() != 4*(8+4) {
		t.Errorf("expected 48 trainable, got %d", m.TrainableParams())
	}
	if m.BaseParams() != 32 {
		t.Errorf("expected 32 frozen, got %d", m.BaseParams())
	}
	if m.Efficiency() <= 0 {
		t.Error("expected positive efficiency")
	}
}

func TestLoRAModelAddBaseInvalid(t *testing.T) {
	m := NewLoRAModel(LoRAConfig{Rank: 2})
	if m.AddBase("bad", nil) == nil {
		t.Error("expected nil weight error")
	}
	v, _ := tensor.New(tensor.Float64, []int{2, 3, 4})
	if m.AddBase("bad", v) == nil {
		t.Error("expected 1-D rejection")
	}
}

func TestLoRAModelTargetFilter(t *testing.T) {
	m := NewLoRAModel(LoRAConfig{Rank: 2, TargetModules: []string{"keep"}})
	m.AddBase("keep.fc", mkWeight(4, 4))
	m.AddBase("skip.fc", mkWeight(4, 4))
	if len(m.Layers()) != 1 {
		t.Errorf("only targeted modules should adapt, got %v", m.Layers())
	}
}

func TestLoRAModelMerge(t *testing.T) {
	m := NewLoRAModel(LoRAConfig{Rank: 1, Alpha: 1})
	w := mkWeight(2, 2)
	m.AddBase("fc", w)
	l, _ := m.Layer("fc")
	// B = [[1],[1]], A = [[1,1]] => delta = [[1,1],[1,1]]
	l.B.Float64()[0] = 1
	l.B.Float64()[1] = 1
	l.A.Float64()[0] = 1
	l.A.Float64()[1] = 1
	if err := m.Merge(); err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 4; i++ {
		if w.Float64()[i] != 1 {
			t.Errorf("element %d: expected 1, got %f", i, w.Float64()[i])
		}
	}
}

func TestLoRAModelDisabledSkipped(t *testing.T) {
	m := NewLoRAModel(LoRAConfig{Rank: 1, Alpha: 1})
	w := mkWeight(2, 2)
	m.AddBase("fc", w)
	l, _ := m.Layer("fc")
	l.SetEnabled(false)
	l.B.Float64()[0] = 1
	l.A.Float64()[0] = 1
	m.Merge()
	if w.Float64()[0] != 0 {
		t.Error("disabled adapter should not merge")
	}
}