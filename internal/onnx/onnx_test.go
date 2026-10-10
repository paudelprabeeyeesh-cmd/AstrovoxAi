package onnx

import (
	"bytes"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

func TestNewModel(t *testing.T) {
	m := NewModel("astrovox", 13)
	if m.Opset != 13 || m.Graph().Name != "main" {
		t.Error("model setup")
	}
	if m.WeightCount() != 0 {
		t.Error("expected empty model")
	}
}

func TestAddTensorAndParamCount(t *testing.T) {
	m := NewModel("test", 13)
	w, _ := tensor.New(tensor.Float64, []int{2, 3})
	if err := m.AddTensor("w", w); err != nil {
		t.Fatal(err)
	}
	if m.WeightCount() != 1 {
		t.Error("weight count")
	}
	if m.ParamCount() != 6 {
		t.Errorf("expected 6 params, got %d", m.ParamCount())
	}
}

func TestAddNode(t *testing.T) {
	m := NewModel("test", 13)
	m.AddNode(NodeProto{Name: "n1", OpType: "MatMul", Inputs: []string{"x", "w"}, Outputs: []string{"y"}})
	if len(m.Graph().Nodes) != 1 {
		t.Fatal("node count")
	}
	n := m.Graph().Nodes[0]
	if n.OpType != "MatMul" || len(n.Inputs) != 2 {
		t.Errorf("node: %+v", n)
	}
}

func TestSerializeRoundTrip(t *testing.T) {
	m := NewModel("astrovox", 17)
	w, _ := tensor.New(tensor.Float64, []int{2, 2})
	w.Float64()[0] = 1.5
	w.Float64()[1] = -2.25
	w.Float64()[2] = 0
	w.Float64()[3] = 100
	if err := m.AddTensor("w", w); err != nil {
		t.Fatal(err)
	}
	m.AddNode(NodeProto{Name: "mm", OpType: "MatMul", Inputs: []string{"a", "w"}, Outputs: []string{"b"}})

	var buf bytes.Buffer
	if err := Serialize(&buf, m); err != nil {
		t.Fatal(err)
	}

	back, err := Deserialize(&buf)
	if err != nil {
		t.Fatal(err)
	}
	if back.Opset != 17 {
		t.Errorf("opset: %d", back.Opset)
	}
	if len(back.Graph().Nodes) != 1 {
		t.Error("nodes")
	}
	ws, ok := back.Tensor("w")
	if !ok {
		t.Fatal("expected tensor w")
	}
	if ws.Dims[0] != 2 || ws.Dims[1] != 2 {
		t.Errorf("dims: %v", ws.Dims)
	}
	if ws.Float64s[0] != 1.5 || ws.Float64s[3] != 100 {
		t.Errorf("data: %v", ws.Float64s)
	}
}

func TestImportExport(t *testing.T) {
	w1, _ := tensor.New(tensor.Float64, []int{2, 2})
	w1.Float64()[0] = 3
	w2, _ := tensor.New(tensor.Float64, []int{3})
	w2.Float64()[1] = 7

	m, err := Import("model", map[string]*tensor.Tensor{"w1": w1, "w2": w2})
	if err != nil {
		t.Fatal(err)
	}
	if m.WeightCount() != 2 {
		t.Errorf("expected 2 weights, got %d", m.WeightCount())
	}
	weights, err := Export(m)
	if err != nil {
		t.Fatal(err)
	}
	if len(weights) != 2 {
		t.Fatal("export count")
	}
	if weights["w1"].Float64()[0] != 3 {
		t.Error("w1 value")
	}
	if weights["w2"].Float64()[1] != 7 {
		t.Error("w2 value")
	}
}

func TestAddNilTensor(t *testing.T) {
	m := NewModel("t", 13)
	if m.AddTensor("x", nil) == nil {
		t.Error("expected nil tensor error")
	}
	if m.AddInitializer(nil) == nil {
		t.Error("expected nil proto error")
	}
}

func TestDeserializeBadMagic(t *testing.T) {
	if _, err := Deserialize(bytes.NewReader([]byte("XXXX"))); err == nil {
		t.Error("expected invalid magic error")
	}
}

func TestDataTypeString(t *testing.T) {
	if DTFloat32.String() != "float32" || DTInt64.String() != "int64" {
		t.Error("dtype strings")
	}
	if DTUndefined.String() != "undefined" {
		t.Error("undefined")
	}
}

func TestTensorProtoToTensorUnsupported(t *testing.T) {
	p := &TensorProto{DataType: DTString, Dims: []int64{1}}
	if _, err := p.ToTensor(); err == nil {
		t.Error("expected unsupported type error")
	}
}

func TestTensorProtoDims(t *testing.T) {
	p := &TensorProto{Name: "t", Dims: []int64{2, 3}, DataType: DTFloat64, Float64s: make([]float64, 6)}
	if p.Dims[0]*p.Dims[1] != 6 {
		t.Error("dims")
	}
	if len(p.Float64s) != 6 {
		t.Error("data length")
	}
}
