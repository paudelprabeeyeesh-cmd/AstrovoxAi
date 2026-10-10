// Package onnx provides a minimal ONNX model reader/writer sufficient
// for importing and exporting linear graphs of tensors.
package onnx

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"math"

	"github.com/astrovox/astrovox/tensor"
)

// DataType identifies an ONNX tensor element type.
type DataType int

const (
	DTUndefined DataType = iota
	DTFloat32
	DTUint8
	DTInt8
	DTUint16
	DTInt16
	DTInt32
	DTInt64
	DTString
	DTBool
	DTFloat16
	DTFloat64
	DTUint32
	DTUint64
)

// String renders the data type.
func (d DataType) String() string {
	switch d {
	case DTFloat32:
		return "float32"
	case DTFloat16:
		return "float16"
	case DTFloat64:
		return "float64"
	case DTInt8:
		return "int8"
	case DTInt16:
		return "int16"
	case DTInt32:
		return "int32"
	case DTInt64:
		return "int64"
	case DTUint8:
		return "uint8"
	case DTUint16:
		return "uint16"
	case DTUint32:
		return "uint32"
	case DTUint64:
		return "uint64"
	case DTBool:
		return "bool"
	default:
		return "undefined"
	}
}

// dtypeToONNX maps tensor.DataType to ONNX DataType.
func dtypeToONNX(d tensor.DType) DataType {
	switch d {
	case tensor.Float32:
		return DTFloat32
	case tensor.Float64:
		return DTFloat64
	case tensor.Int8:
		return DTInt8
	case tensor.Int16:
		return DTInt16
	case tensor.Int32:
		return DTInt32
	case tensor.Int64:
		return DTInt64
	case tensor.Uint8:
		return DTUint8
	case tensor.Uint16:
		return DTUint16
	case tensor.Uint32:
		return DTUint32
	case tensor.Uint64:
		return DTUint64
	case tensor.Bool:
		return DTBool
	default:
		return DTUndefined
	}
}

// TensorProto is a minimal ONNX tensor representation.
type TensorProto struct {
	Name     string
	Dims     []int64
	DataType DataType
	Float32s []float32
	Float64s []float64
	Int32s   []int32
	Int64s   []int64
	RawData  []byte
}

// ToTensor converts a TensorProto to a tensor.Tensor.
func (p *TensorProto) ToTensor() (*tensor.Tensor, error) {
	dims := make([]int, len(p.Dims))
	for i, d := range p.Dims {
		dims[i] = int(d)
	}
	switch p.DataType {
	case DTFloat32:
		t, err := tensor.New(tensor.Float32, dims)
		if err != nil {
			return nil, err
		}
		dst := t.Float32()
		for i, v := range p.Float32s {
			if i < len(dst) {
				dst[i] = v
			}
		}
		return t, nil
	case DTFloat64:
		t, err := tensor.New(tensor.Float64, dims)
		if err != nil {
			return nil, err
		}
		copy(t.Float64(), p.Float64s)
		return t, nil
	case DTInt32:
		t, err := tensor.New(tensor.Int32, dims)
		if err != nil {
			return nil, err
		}
		dst := t.Int32()
		for i, v := range p.Int32s {
			if i < len(dst) {
				dst[i] = v
			}
		}
		return t, nil
	case DTInt64:
		t, err := tensor.New(tensor.Int64, dims)
		if err != nil {
			return nil, err
		}
		dst := t.Int64()
		for i, v := range p.Int64s {
			if i < len(dst) {
				dst[i] = v
			}
		}
		return t, nil
	case DTUint8:
		t, err := tensor.New(tensor.Uint8, dims)
		if err != nil {
			return nil, err
		}
		if len(p.RawData) > 0 {
			copy(t.Uint8(), p.RawData)
		}
		return t, nil
	default:
		return nil, fmt.Errorf("unsupported ONNX data type %s", p.DataType)
	}
}

// NewTensorProto builds a TensorProto from a tensor.
func NewTensorProto(name string, t *tensor.Tensor) (*TensorProto, error) {
	if t == nil {
		return nil, errors.New("nil tensor")
	}
	p := &TensorProto{Name: name, DataType: dtypeToONNX(t.DType())}
	for _, d := range t.Shape().Dims() {
		p.Dims = append(p.Dims, int64(d))
	}
	switch p.DataType {
	case DTFloat32:
		p.Float32s = append([]float32(nil), t.Float32()...)
	case DTFloat64:
		p.Float64s = append([]float64(nil), t.Float64()...)
	case DTInt32:
		p.Int32s = append([]int32(nil), t.Int32()...)
	case DTInt64:
		p.Int64s = append([]int64(nil), t.Int64()...)
	case DTUint8:
		p.RawData = append([]byte(nil), t.Uint8()...)
	default:
		return nil, fmt.Errorf("unsupported tensor dtype %v", t.DType())
	}
	return p, nil
}

// NodeProto is an ONNX operation node.
type NodeProto struct {
	Name    string
	OpType  string
	Inputs  []string
	Outputs []string
	Attrs   map[string]interface{}
}

// GraphProto is a minimal ONNX graph.
type GraphProto struct {
	Name         string
	Nodes        []NodeProto
	Inputs       []string
	Outputs      []string
	Initializers map[string]*TensorProto
}

// ModelProto is a minimal ONNX model.
type ModelProto struct {
	ProducerName    string
	ProducerVersion string
	IRVersion       int64
	Opset           int64
	Graphs          []*GraphProto
}

// NewModel creates an empty model.
func NewModel(producer string, opset int64) *ModelProto {
	return &ModelProto{
		ProducerName:    producer,
		ProducerVersion: "1.0",
		IRVersion:       8,
		Opset:           opset,
		Graphs:          []*GraphProto{{Name: "main", Initializers: make(map[string]*TensorProto)}},
	}
}

// Graph returns the main graph.
func (m *ModelProto) Graph() *GraphProto {
	if len(m.Graphs) == 0 {
		m.Graphs = []*GraphProto{{Name: "main", Initializers: make(map[string]*TensorProto)}}
	}
	return m.Graphs[0]
}

// AddNode appends a node to the main graph.
func (m *ModelProto) AddNode(n NodeProto) {
	g := m.Graph()
	g.Nodes = append(g.Nodes, n)
}

// AddInitializer registers a weight tensor.
func (m *ModelProto) AddInitializer(p *TensorProto) error {
	if p == nil {
		return errors.New("nil tensor proto")
	}
	g := m.Graph()
	g.Initializers[p.Name] = p
	return nil
}

// AddTensor adds a weight tensor from a tensor.
func (m *ModelProto) AddTensor(name string, t *tensor.Tensor) error {
	p, err := NewTensorProto(name, t)
	if err != nil {
		return err
	}
	return m.AddInitializer(p)
}

// Tensor returns an initializer by name.
func (m *ModelProto) Tensor(name string) (*TensorProto, bool) {
	p, ok := m.Graph().Initializers[name]
	return p, ok
}

// WeightCount returns the number of initializers.
func (m *ModelProto) WeightCount() int { return len(m.Graph().Initializers) }

// ParamCount returns the total number of initializer elements.
func (m *ModelProto) ParamCount() int64 {
	g := m.Graph()
	total := int64(0)
	for _, p := range g.Initializers {
		n := int64(1)
		for _, d := range p.Dims {
			n *= d
		}
		total += n
	}
	return total
}

// Serialization -----------------------------------------------------------

// Serialize writes the model as a deterministic binary stream.
//
// Format:
//
//	magic "ONXB" | version u32 | opset u64 | producerLen u32 | producer
//	graphNameLen u32 | graphName | nodeCount u32 | nodes
//	initCount u32 | initializers
func Serialize(w io.Writer, m *ModelProto) error {
	if _, err := w.Write([]byte("ONXB")); err != nil {
		return err
	}
	writeU32(w, 1)
	writeU64(w, uint64(m.Opset))
	writeString(w, m.ProducerName)
	g := m.Graph()
	writeString(w, g.Name)
	writeU32(w, uint32(len(g.Nodes)))
	for _, n := range g.Nodes {
		writeString(w, n.Name)
		writeString(w, n.OpType)
		writeU32(w, uint32(len(n.Inputs)))
		for _, in := range n.Inputs {
			writeString(w, in)
		}
		writeU32(w, uint32(len(n.Outputs)))
		for _, out := range n.Outputs {
			writeString(w, out)
		}
	}
	writeU32(w, uint32(len(g.Initializers)))
	for _, p := range g.Initializers {
		if err := writeTensorProto(w, p); err != nil {
			return err
		}
	}
	return nil
}

func writeTensorProto(w io.Writer, p *TensorProto) error {
	writeString(w, p.Name)
	writeU64(w, uint64(len(p.Dims)))
	for _, d := range p.Dims {
		writeU64(w, uint64(d))
	}
	writeU32(w, uint32(p.DataType))
	var count uint64
	switch p.DataType {
	case DTFloat32:
		count = uint64(len(p.Float32s))
	case DTFloat64:
		count = uint64(len(p.Float64s))
	case DTInt32:
		count = uint64(len(p.Int32s))
	case DTInt64:
		count = uint64(len(p.Int64s))
	default:
		count = uint64(len(p.RawData))
	}
	writeU64(w, count)
	switch p.DataType {
	case DTFloat32:
		for _, v := range p.Float32s {
			writeU32(w, math.Float32bits(v))
		}
	case DTFloat64:
		for _, v := range p.Float64s {
			writeU64(w, math.Float64bits(v))
		}
	case DTInt32:
		for _, v := range p.Int32s {
			writeU32(w, uint32(v))
		}
	case DTInt64:
		for _, v := range p.Int64s {
			writeU64(w, uint64(v))
		}
	default:
		if _, err := w.Write(p.RawData); err != nil {
			return err
		}
	}
	return nil
}

// Deserialize reads a model from the stream produced by Serialize.
func Deserialize(r io.Reader) (*ModelProto, error) {
	magic := make([]byte, 4)
	if _, err := io.ReadFull(r, magic); err != nil {
		return nil, err
	}
	if string(magic) != "ONXB" {
		return nil, errors.New("invalid ONNX magic")
	}
	if _, err := readU32(r); err != nil {
		return nil, err
	}
	opset, err := readU64(r)
	if err != nil {
		return nil, err
	}
	producer, err := readString(r)
	if err != nil {
		return nil, err
	}
	graphName, err := readString(r)
	if err != nil {
		return nil, err
	}
	m := NewModel(producer, int64(opset))
	g := m.Graph()
	g.Name = graphName

	nodeCount, err := readU32(r)
	if err != nil {
		return nil, err
	}
	for i := uint32(0); i < nodeCount; i++ {
		n, err := readNodeProto(r)
		if err != nil {
			return nil, err
		}
		g.Nodes = append(g.Nodes, *n)
	}
	initCount, err := readU32(r)
	if err != nil {
		return nil, err
	}
	for i := uint32(0); i < initCount; i++ {
		p, err := readTensorProto(r)
		if err != nil {
			return nil, err
		}
		g.Initializers[p.Name] = p
	}
	return m, nil
}

func readNodeProto(r io.Reader) (*NodeProto, error) {
	n := &NodeProto{Attrs: map[string]interface{}{}}
	var err error
	if n.Name, err = readString(r); err != nil {
		return nil, err
	}
	if n.OpType, err = readString(r); err != nil {
		return nil, err
	}
	inCount, err := readU32(r)
	if err != nil {
		return nil, err
	}
	for i := uint32(0); i < inCount; i++ {
		s, err := readString(r)
		if err != nil {
			return nil, err
		}
		n.Inputs = append(n.Inputs, s)
	}
	outCount, err := readU32(r)
	if err != nil {
		return nil, err
	}
	for i := uint32(0); i < outCount; i++ {
		s, err := readString(r)
		if err != nil {
			return nil, err
		}
		n.Outputs = append(n.Outputs, s)
	}
	return n, nil
}

func readTensorProto(r io.Reader) (*TensorProto, error) {
	p := &TensorProto{}
	var err error
	if p.Name, err = readString(r); err != nil {
		return nil, err
	}
	nDims, err := readU64(r)
	if err != nil {
		return nil, err
	}
	for i := uint64(0); i < nDims; i++ {
		d, err := readU64(r)
		if err != nil {
			return nil, err
		}
		p.Dims = append(p.Dims, int64(d))
	}
	dt, err := readU32(r)
	if err != nil {
		return nil, err
	}
	p.DataType = DataType(dt)
	count, err := readU64(r)
	if err != nil {
		return nil, err
	}
	switch p.DataType {
	case DTFloat32:
		p.Float32s = make([]float32, count)
		for i := range p.Float32s {
			b, err := readU32(r)
			if err != nil {
				return nil, err
			}
			p.Float32s[i] = math.Float32frombits(b)
		}
	case DTFloat64:
		p.Float64s = make([]float64, count)
		for i := range p.Float64s {
			b, err := readU64(r)
			if err != nil {
				return nil, err
			}
			p.Float64s[i] = math.Float64frombits(b)
		}
	case DTInt32:
		p.Int32s = make([]int32, count)
		for i := range p.Int32s {
			b, err := readU32(r)
			if err != nil {
				return nil, err
			}
			p.Int32s[i] = int32(b)
		}
	case DTInt64:
		p.Int64s = make([]int64, count)
		for i := range p.Int64s {
			b, err := readU64(r)
			if err != nil {
				return nil, err
			}
			p.Int64s[i] = int64(b)
		}
	default:
		p.RawData = make([]byte, count)
		if _, err := io.ReadFull(r, p.RawData); err != nil {
			return nil, err
		}
	}
	return p, nil
}

func writeU32(w io.Writer, v uint32) {
	_ = binary.Write(w, binary.LittleEndian, v)
}

func writeU64(w io.Writer, v uint64) {
	_ = binary.Write(w, binary.LittleEndian, v)
}

func writeString(w io.Writer, s string) {
	writeU32(w, uint32(len(s)))
	_, _ = w.Write([]byte(s))
}

func readU32(r io.Reader) (uint32, error) {
	var v uint32
	if err := binary.Read(r, binary.LittleEndian, &v); err != nil {
		return 0, err
	}
	return v, nil
}

func readU64(r io.Reader) (uint64, error) {
	var v uint64
	if err := binary.Read(r, binary.LittleEndian, &v); err != nil {
		return 0, err
	}
	return v, nil
}

func readString(r io.Reader) (string, error) {
	n, err := readU32(r)
	if err != nil {
		return "", err
	}
	buf := make([]byte, n)
	if _, err := io.ReadFull(r, buf); err != nil {
		return "", err
	}
	return string(buf), nil
}

// Import builds a model from tensors, importing weights by name.
func Import(name string, weights map[string]*tensor.Tensor) (*ModelProto, error) {
	m := NewModel(name, 13)
	for n, t := range weights {
		if err := m.AddTensor(n, t); err != nil {
			return nil, err
		}
	}
	return m, nil
}

// Export extracts all initializers as tensors.
func Export(m *ModelProto) (map[string]*tensor.Tensor, error) {
	out := make(map[string]*tensor.Tensor)
	for n, p := range m.Graph().Initializers {
		t, err := p.ToTensor()
		if err != nil {
			return nil, err
		}
		out[n] = t
	}
	return out, nil
}
