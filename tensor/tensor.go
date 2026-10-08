package tensor

import (
	"strconv"
	"strings"
	"unsafe"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor/broadcast"
	"github.com/astrovox/astrovox/tensor/iterator"
	"github.com/astrovox/astrovox/tensor/memory"
	"github.com/astrovox/astrovox/tensor/reshape"
	"github.com/astrovox/astrovox/tensor/transpose"
)

// Storage is a reference-counted (GC-managed) aligned byte buffer
// holding tensor elements. Views share the same Storage.
type Storage struct {
	data  []byte
	dtype DType
	numel int
}

// NewStorage allocates an aligned storage for numel elements.
func NewStorage(dtype DType, numel int) (*Storage, error) {
	if numel < 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "negative element count")
	}
	size := dtype.Size() * numel
	if size < 1 {
		// Typed views take &data[0]; keep a 1-byte
		// backing for empty storages. The element
		// count still bounds all access.
		size = 1
	}
	return &Storage{
		data:  memory.AlignedAlloc(size, memory.DefaultAlignment),
		dtype: dtype,
		numel: numel,
	}, nil
}

// DType returns the storage element type.
func (s *Storage) DType() DType { return s.dtype }

// Numel returns the storage element count.
func (s *Storage) Numel() int { return s.numel }

// Bytes returns the raw backing bytes.
func (s *Storage) Bytes() []byte { return s.data }

// Tensor is a multi-dimensional array view over a Storage.
// A Tensor may share its Storage with other views (zero-copy).
type Tensor struct {
	st      *Storage
	offset  int // element offset into storage
	shape   Shape
	strides []int // element strides
	view    bool
	base    *Tensor
}

// New creates a tensor with the given dtype and shape.
func New(dtype DType, shape []int) (*Tensor, error) {
	s, err := NewShape(shape...)
	if err != nil {
		return nil, err
	}
	st, err := NewStorage(dtype, s.NumElements())
	if err != nil {
		return nil, err
	}
	return &Tensor{
		st:      st,
		shape:   s,
		strides: broadcast.RowMajorStrides(shape),
	}, nil
}

// Zeros creates a zero-filled tensor.
func Zeros(dtype DType, shape []int) (*Tensor, error) {
	t, err := New(dtype, shape)
	if err != nil {
		return nil, err
	}
	return t, nil
}

// Ones creates a tensor filled with ones.
func Ones(dtype DType, shape []int) (*Tensor, error) {
	t, err := New(dtype, shape)
	if err != nil {
		return nil, err
	}
	return Fill(t, 1)
}

// Full creates a tensor filled with value.
func Full(dtype DType, shape []int, value float64) (*Tensor, error) {
	t, err := New(dtype, shape)
	if err != nil {
		return nil, err
	}
	return Fill(t, value)
}

// Fill sets every element of t to value in place.
func Fill(t *Tensor, value float64) (*Tensor, error) {
	if t == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	n := t.shape.NumElements()
	switch t.st.dtype {
	case Float32:
		v := float32(value)
		s := t.Float32()
		for i := range s {
			s[i] = v
		}
	case Float64:
		s := t.Float64()
		for i := range s {
			s[i] = value
		}
	case Int8:
		s := t.Int8()
		for i := range s {
			s[i] = int8(value)
		}
	case Int16:
		s := t.Int16()
		for i := range s {
			s[i] = int16(value)
		}
	case Int32:
		s := t.Int32()
		for i := range s {
			s[i] = int32(value)
		}
	case Int64:
		s := t.Int64()
		for i := range s {
			s[i] = int64(value)
		}
	case Uint8:
		s := t.Uint8()
		for i := range s {
			s[i] = uint8(value)
		}
	case Uint16:
		s := t.Uint16()
		for i := range s {
			s[i] = uint16(value)
		}
	case Uint32:
		s := t.Uint32()
		for i := range s {
			s[i] = uint32(value)
		}
	case Uint64:
		s := t.Uint64()
		for i := range s {
			s[i] = uint64(value)
		}
	case Bool:
		s := t.Bool()
		for i := range s {
			s[i] = value != 0
		}
	case Float16:
		s := t.Float16View()
		bits := Float16bits(float32(value))
		for i := range s {
			s[i] = bits
		}
	case BFloat16:
		s := t.BFloat16View()
		bits := BFloat16bits(float32(value))
		for i := range s {
			s[i] = bits
		}
	case Complex64:
		s := t.Complex64()
		v := complex(float32(value), 0)
		for i := range s {
			s[i] = v
		}
	case Complex128:
		s := t.Complex128()
		v := complex(value, 0)
		for i := range s {
			s[i] = v
		}
	default:
		return nil, errors.New(errors.CodeUnimplemented, "Fill for dtype").
			WithField("dtype", t.st.dtype.String())
	}
	_ = n
	return t, nil
}

// Arange creates a 1-D tensor [start, stop) with step.
func Arange(dtype DType, start, stop, step float64) (*Tensor, error) {
	if step == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "zero step")
	}
	n := 0
	if step > 0 {
		for v := start; v < stop; v += step {
			n++
		}
	} else {
		for v := start; v > stop; v += step {
			n++
		}
	}
	t, err := New(dtype, []int{n})
	if err != nil {
		return nil, err
	}
	switch dtype {
	case Float32:
		s := t.Float32()
		for i := range s {
			s[i] = float32(start + float64(i)*step)
		}
	case Float64:
		s := t.Float64()
		for i := range s {
			s[i] = start + float64(i)*step
		}
	case Int64:
		s := t.Int64()
		for i := range s {
			s[i] = int64(start + float64(i)*step)
		}
	default:
		return nil, errors.New(errors.CodeUnimplemented, "Arange for dtype").
			WithField("dtype", dtype.String())
	}
	return t, nil
}

// Shape returns the tensor shape.
func (t *Tensor) Shape() Shape { return t.shape }

// DType returns the element type.
func (t *Tensor) DType() DType { return t.st.dtype }

// Strides returns the element strides.
func (t *Tensor) Strides() []int { return t.strides }

// NumElements returns the element count of the view.
func (t *Tensor) NumElements() int { return t.shape.NumElements() }

// StorageOffset returns the element offset into the storage.
func (t *Tensor) StorageOffset() int { return t.offset }

// IsContiguous reports whether the view is row-major contiguous.
func (t *Tensor) IsContiguous() bool {
	expected := broadcast.RowMajorStrides(t.shape.Dims())
	for i := range expected {
		if t.strides[i] != expected[i] {
			return false
		}
	}
	return true
}

// IsView reports whether the tensor shares storage with a parent.
func (t *Tensor) IsView() bool { return t.view }

// Base returns the root tensor of the view chain.
func (t *Tensor) Base() *Tensor {
	cur := t
	for cur.view && cur.base != nil {
		cur = cur.base
	}
	return cur
}

// Float32 returns a zero-copy typed view of the underlying
// storage segment. Valid only for contiguous Float32 tensors.
func (t *Tensor) Float32() []float32 {
	if t.st.dtype != Float32 {
		return nil
	}
	base := unsafe.Slice((*float32)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Float64 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Float64() []float64 {
	if t.st.dtype != Float64 {
		return nil
	}
	base := unsafe.Slice((*float64)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Int64 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Int64() []int64 {
	if t.st.dtype != Int64 {
		return nil
	}
	base := unsafe.Slice((*int64)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Int32 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Int32() []int32 {
	if t.st.dtype != Int32 {
		return nil
	}
	base := unsafe.Slice((*int32)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Int returns a zero-copy typed view (contiguous only).
func (t *Tensor) Int() []int {
	if t.st.dtype != Int64 {
		return nil
	}
	base := unsafe.Slice((*int64)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	out := make([]int, t.shape.NumElements())
	for i, v := range base[t.offset : t.offset+t.shape.NumElements()] {
		out[i] = int(v)
	}
	return out
}

// Uint8 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Uint8() []uint8 {
	if t.st.dtype != Uint8 {
		return nil
	}
	base := unsafe.Slice((*uint8)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Int8 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Int8() []int8 {
	if t.st.dtype != Int8 {
		return nil
	}
	base := unsafe.Slice((*int8)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Int16 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Int16() []int16 {
	if t.st.dtype != Int16 {
		return nil
	}
	base := unsafe.Slice((*int16)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Uint16 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Uint16() []uint16 {
	if t.st.dtype != Uint16 {
		return nil
	}
	base := unsafe.Slice((*uint16)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Uint32 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Uint32() []uint32 {
	if t.st.dtype != Uint32 {
		return nil
	}
	base := unsafe.Slice((*uint32)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Uint64 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Uint64() []uint64 {
	if t.st.dtype != Uint64 {
		return nil
	}
	base := unsafe.Slice((*uint64)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Bool returns a zero-copy typed view (contiguous only).
func (t *Tensor) Bool() []bool {
	if t.st.dtype != Bool {
		return nil
	}
	base := unsafe.Slice((*bool)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Complex128 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Complex128() []complex128 {
	if t.st.dtype != Complex128 {
		return nil
	}
	base := unsafe.Slice((*complex128)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Complex64 returns a zero-copy typed view (contiguous only).
func (t *Tensor) Complex64() []complex64 {
	if t.st.dtype != Complex64 {
		return nil
	}
	base := unsafe.Slice((*complex64)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Float16View returns the raw binary16 bits (contiguous only).
func (t *Tensor) Float16View() []uint16 {
	if t.st.dtype != Float16 {
		return nil
	}
	base := unsafe.Slice((*uint16)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// BFloat16View returns the raw bfloat16 bits (contiguous only).
func (t *Tensor) BFloat16View() []uint16 {
	if t.st.dtype != BFloat16 {
		return nil
	}
	base := unsafe.Slice((*uint16)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
	return base[t.offset : t.offset+t.shape.NumElements()]
}

// Get returns the element value at idx.
func (t *Tensor) Get(idx ...int) (any, error) {
	off, err := t.indexOf(idx)
	if err != nil {
		return nil, err
	}
	switch t.st.dtype {
	case Float32:
		return t.Float32()[off], nil
	case Float64:
		return t.Float64()[off], nil
	case Int8:
		return t.Int8()[off], nil
	case Int16:
		return t.Int16()[off], nil
	case Int32:
		return t.Int32()[off], nil
	case Int64:
		return t.Int64()[off], nil
	case Uint8:
		return t.Uint8()[off], nil
	case Uint16:
		return t.Uint16()[off], nil
	case Uint32:
		return t.Uint32()[off], nil
	case Uint64:
		return t.Uint64()[off], nil
	case Bool:
		return t.Bool()[off], nil
	case Float16:
		return t.Float16View()[off], nil
	case BFloat16:
		return t.BFloat16View()[off], nil
	case Complex64:
		return t.Complex64()[off], nil
	case Complex128:
		return t.Complex128()[off], nil
	default:
		return nil, errors.New(errors.CodeUnimplemented, "Get for dtype").
			WithField("dtype", t.st.dtype.String())
	}
}

// Set writes value at idx.
func (t *Tensor) Set(value any, idx ...int) error {
	off, err := t.indexOf(idx)
	if err != nil {
		return err
	}
	switch t.st.dtype {
	case Float32:
		t.Float32()[off] = float32(toFloat(value))
	case Float64:
		t.Float64()[off] = toFloat(value)
	case Int8:
		t.Int8()[off] = int8(toFloat(value))
	case Int16:
		t.Int16()[off] = int16(toFloat(value))
	case Int32:
		t.Int32()[off] = int32(toFloat(value))
	case Int64:
		t.Int64()[off] = int64(toFloat(value))
	case Uint8:
		t.Uint8()[off] = uint8(toFloat(value))
	case Uint16:
		t.Uint16()[off] = uint16(toFloat(value))
	case Uint32:
		t.Uint32()[off] = uint32(toFloat(value))
	case Uint64:
		t.Uint64()[off] = uint64(toFloat(value))
	case Bool:
		t.Bool()[off] = toFloat(value) != 0
	case Float16:
		t.Float16View()[off] = Float16bits(float32(toFloat(value)))
	case BFloat16:
		t.BFloat16View()[off] = BFloat16bits(float32(toFloat(value)))
	case Complex64:
		t.Complex64()[off] = toComplex64(value)
	case Complex128:
		t.Complex128()[off] = toComplex128(value)
	default:
		return errors.New(errors.CodeUnimplemented, "Set for dtype").
			WithField("dtype", t.st.dtype.String())
	}
	return nil
}

func toFloat(v any) float64 {
	switch x := v.(type) {
	case float64:
		return x
	case float32:
		return float64(x)
	case int:
		return float64(x)
	case int8:
		return float64(x)
	case int16:
		return float64(x)
	case int32:
		return float64(x)
	case int64:
		return float64(x)
	case uint:
		return float64(x)
	case uint8:
		return float64(x)
	case uint16:
		return float64(x)
	case uint32:
		return float64(x)
	case uint64:
		return float64(x)
	case bool:
		if x {
			return 1
		}
		return 0
	case complex64:
		return float64(real(x))
	case complex128:
		return real(x)
	default:
		return 0
	}
}

// toComplex64 coerces a scalar value to complex64.
func toComplex64(v any) complex64 {
	switch x := v.(type) {
	case complex64:
		return x
	case complex128:
		return complex64(x)
	default:
		return complex(float32(toFloat(v)), 0)
	}
}

// toComplex128 coerces a scalar value to complex128.
func toComplex128(v any) complex128 {
	switch x := v.(type) {
	case complex128:
		return x
	case complex64:
		return complex128(x)
	default:
		return complex(toFloat(v), 0)
	}
}

func (t *Tensor) indexOf(idx []int) (int, error) {
	if len(idx) != t.shape.Rank() {
		return 0, errors.New(errors.CodeInvalidArgument, "index rank mismatch").
			WithField("got", len(idx)).WithField("want", t.shape.Rank())
	}
	off := t.offset
	for i, v := range idx {
		if v < 0 || v >= t.shape.Dim(i) {
			return 0, errors.New(errors.CodeOutOfRange, "index out of range").
				WithField("dim", i).WithField("index", v).WithField("size", t.shape.Dim(i))
		}
		off += v * t.strides[i]
	}
	return off, nil
}

// Reshape returns a tensor with newShape, zero-copy when the
// memory layout permits, otherwise a contiguous copy.
func (t *Tensor) Reshape(dims ...int) (*Tensor, error) {
	target, err := reshape.InferShape(t.shape.Dims(), dims)
	if err != nil {
		return nil, err
	}
	if reshape.CanView(t.shape.Dims(), t.strides, target) {
		out := *t
		out.shape = MustShape(target...)
		out.strides = broadcast.RowMajorStrides(target)
		out.view = true
		out.base = t
		return &out, nil
	}
	contig, err := t.Contiguous()
	if err != nil {
		return nil, err
	}
	out := *contig
	out.shape = MustShape(target...)
	out.strides = broadcast.RowMajorStrides(target)
	return &out, nil
}

// Contiguous returns a row-major contiguous copy when the view
// is not already contiguous; otherwise returns t unchanged.
func (t *Tensor) Contiguous() (*Tensor, error) {
	if t.IsContiguous() {
		return t, nil
	}
	out, err := New(t.st.dtype, t.shape.Dims())
	if err != nil {
		return nil, err
	}
	if err := copyViaIterator(t, out); err != nil {
		return nil, err
	}
	return out, nil
}

func copyViaIterator(src, dst *Tensor) error {
	it, err := iterator.NewIterator(
		iterator.InputSpec{Shape: src.shape.Dims(), Strides: src.strides},
		iterator.InputSpec{Shape: dst.shape.Dims(), Strides: dst.strides},
	)
	if err != nil {
		return err
	}
	// The iterator yields offsets relative to the
	// storage origin; add the source's storage
	// offset and index the raw backing storage,
	// because typed accessors like Float64()
	// return contiguous-only sub-slices that
	// panic on broadcast and sliced views.
	switch src.st.dtype {
	case Float32:
		s := rawFloat32(src)
		d := dst.Float32()
		for it.Next() {
			d[it.OutputOffset()] = s[src.offset+it.InputOffset(0)]
		}
	case Float64:
		s := rawFloat64(src)
		d := dst.Float64()
		for it.Next() {
			d[it.OutputOffset()] = s[src.offset+it.InputOffset(0)]
		}
	case Int64:
		s := rawInt64(src)
		d := dst.Int64()
		for it.Next() {
			d[it.OutputOffset()] = s[src.offset+it.InputOffset(0)]
		}
	case Int32:
		s := rawInt32(src)
		d := dst.Int32()
		for it.Next() {
			d[it.OutputOffset()] = s[src.offset+it.InputOffset(0)]
		}
	case Uint8:
		s := rawUint8(src)
		d := dst.Uint8()
		for it.Next() {
			d[it.OutputOffset()] = s[src.offset+it.InputOffset(0)]
		}
	case Bool:
		s := rawBool(src)
		d := dst.Bool()
		for it.Next() {
			d[it.OutputOffset()] = s[src.offset+it.InputOffset(0)]
		}
	default:
		return errors.New(errors.CodeUnimplemented, "contiguous copy for dtype").
			WithField("dtype", src.st.dtype.String())
	}
	return nil
}

// rawFloat64 returns the full typed backing
// storage without the contiguous sub-slice.
func rawFloat64(t *Tensor) []float64 {
	return unsafe.Slice((*float64)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
}

func rawFloat32(t *Tensor) []float32 {
	return unsafe.Slice((*float32)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
}

func rawInt64(t *Tensor) []int64 {
	return unsafe.Slice((*int64)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
}

func rawInt32(t *Tensor) []int32 {
	return unsafe.Slice((*int32)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
}

func rawUint8(t *Tensor) []uint8 {
	return unsafe.Slice((*uint8)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
}

func rawBool(t *Tensor) []bool {
	return unsafe.Slice((*bool)(unsafe.Pointer(&t.st.data[0])), t.st.numel)
}

// Transpose swaps two dimensions as a zero-copy view.
func (t *Tensor) Transpose(d0, d1 int) (*Tensor, error) {
	perm, err := transpose.SwapDims(t.shape.Rank(), d0, d1)
	if err != nil {
		return nil, err
	}
	return t.Permute(perm)
}

// Permute returns a zero-copy view with dimensions reordered.
func (t *Tensor) Permute(perm []int) (*Tensor, error) {
	if err := transpose.ValidatePerm(t.shape.Rank(), perm); err != nil {
		return nil, err
	}
	out := *t
	out.shape = MustShape(transpose.PermutedShape(t.shape.Dims(), perm)...)
	out.strides = transpose.PermutedStrides(t.strides, perm)
	out.view = true
	out.base = t
	return &out, nil
}

// Slice returns a zero-copy view over [begins, ends) per dimension.
func (t *Tensor) Slice(begins, ends []int) (*Tensor, error) {
	rank := t.shape.Rank()
	if len(begins) != rank || len(ends) != rank {
		return nil, errors.New(errors.CodeInvalidArgument, "slice rank mismatch").
			WithField("rank", rank)
	}
	shape := make([]int, rank)
	offset := t.offset
	for i := range shape {
		b, e := begins[i], ends[i]
		if b < 0 {
			b += t.shape.Dim(i)
		}
		if e < 0 {
			e += t.shape.Dim(i)
		}
		if b < 0 || e > t.shape.Dim(i) || b > e {
			return nil, errors.New(errors.CodeInvalidArgument, "invalid slice bounds").
				WithField("dim", i).WithField("begin", b).WithField("end", e).
				WithField("size", t.shape.Dim(i))
		}
		shape[i] = e - b
		offset += b * t.strides[i]
	}
	out := *t
	out.offset = offset
	out.shape = MustShape(shape...)
	out.view = true
	out.base = t
	return &out, nil
}

// Expand returns a zero-copy view virtually broadcast to dims.
func (t *Tensor) Expand(dims ...int) (*Tensor, error) {
	target, err := broadcast.BroadcastShapes(t.shape.Dims(), dims)
	if err != nil {
		return nil, err
	}
	strides, err := broadcast.BroadcastStrides(t.shape.Dims(), t.strides, target)
	if err != nil {
		return nil, err
	}
	out := *t
	out.shape = MustShape(target...)
	out.strides = strides
	out.view = true
	out.base = t
	return &out, nil
}

// Clone returns a deep copy with its own storage.
func (t *Tensor) Clone() (*Tensor, error) {
	out, err := New(t.st.dtype, t.shape.Dims())
	if err != nil {
		return nil, err
	}
	if err := copyViaIterator(t, out); err != nil {
		return nil, err
	}
	return out, nil
}

// Equal compares shape, dtype, and element values.
func (t *Tensor) Equal(o *Tensor) (bool, error) {
	if t == nil || o == nil {
		return false, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if !t.shape.Equal(o.shape) {
		return false, nil
	}
	if t.st.dtype != o.st.dtype {
		return false, nil
	}
	if t.NumElements() != o.NumElements() {
		return false, nil
	}
	switch t.st.dtype {
	case Float32:
		a, b := t.Float32(), o.Float32()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Float64:
		a, b := t.Float64(), o.Float64()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Int64:
		a, b := t.Int64(), o.Int64()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Int32:
		a, b := t.Int32(), o.Int32()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Uint8:
		a, b := t.Uint8(), o.Uint8()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Bool:
		a, b := t.Bool(), o.Bool()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Int8:
		a, b := t.Int8(), o.Int8()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Int16:
		a, b := t.Int16(), o.Int16()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Uint16:
		a, b := t.Uint16(), o.Uint16()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Uint32:
		a, b := t.Uint32(), o.Uint32()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Uint64:
		a, b := t.Uint64(), o.Uint64()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Float16:
		a, b := t.Float16View(), o.Float16View()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case BFloat16:
		a, b := t.BFloat16View(), o.BFloat16View()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Complex64:
		a, b := t.Complex64(), o.Complex64()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	case Complex128:
		a, b := t.Complex128(), o.Complex128()
		for i := range a {
			if a[i] != b[i] {
				return false, nil
			}
		}
	default:
		return false, errors.New(errors.CodeUnimplemented, "Equal for dtype").
			WithField("dtype", t.st.dtype.String())
	}
	return true, nil
}

// String renders a compact tensor summary.
func (t *Tensor) String() string {
	var b strings.Builder
	b.WriteString(t.st.dtype.String())
	b.WriteString(t.shape.String())
	if t.view {
		b.WriteString(" view")
	}
	if t.NumElements() <= 8 {
		b.WriteString(" [")
		for i := 0; i < t.NumElements(); i++ {
			if i > 0 {
				b.WriteString(" ")
			}
			switch t.st.dtype {
			case Float32:
				b.WriteString(floatString(float64(t.Float32()[i])))
			case Float64:
				b.WriteString(floatString(t.Float64()[i]))
			case Int64:
				b.WriteString(intString(t.Int64()[i]))
			case Int32:
				b.WriteString(intString(int64(t.Int32()[i])))
			case Uint8:
				b.WriteString(intString(int64(t.Uint8()[i])))
			case Bool:
				if t.Bool()[i] {
					b.WriteString("true")
				} else {
					b.WriteString("false")
				}
			}
		}
		b.WriteString("]")
	}
	return b.String()
}

func floatString(f float64) string {
	return strconv.FormatFloat(f, 'g', -1, 64)
}

func intString(i int64) string {
	if i == 0 {
		return "0"
	}
	neg := i < 0
	if neg {
		i = -i
	}
	var buf [20]byte
	pos := len(buf)
	for i > 0 {
		pos--
		buf[pos] = byte('0' + i%10)
		i /= 10
	}
	if neg {
		pos--
		buf[pos] = '-'
	}
	return string(buf[pos:])
}
