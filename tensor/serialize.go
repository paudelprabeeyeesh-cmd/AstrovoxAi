package tensor

import (
	"encoding/binary"
	"io"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/internal/utils"
)

// Serialization format v1:
//   magic (4B "ASTV") | format version (uint16) | dtype (uint16)
//   rank (uint16) | shape (rank x uint64) | strides (rank x int64)
//   offset (uint64) | payload length (uint64) | payload | checksum (uint64)

const (
	formatMagic   = "ASTV"
	formatVersion = uint16(1)
	headerSize    = 4 + 2 + 2 + 2
)

// Save serializes t to a deterministic byte stream.
func Save(t *Tensor) ([]byte, error) {
	if t == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "nil tensor")
	}
	if !t.IsContiguous() {
		c, err := t.Contiguous()
		if err != nil {
			return nil, err
		}
		t = c
	}
	rank := t.shape.Rank()
	numel := t.shape.NumElements()
	payloadSize := t.st.dtype.Size() * numel
	buf := make([]byte, 0, headerSize+2*16*rank+16+payloadSize+8)
	buf = append(buf, formatMagic...)
	buf = appendU16(buf, formatVersion)
	buf = appendU16(buf, uint16(t.st.dtype))
	buf = appendU16(buf, uint16(rank))
	for _, d := range t.shape.Dims() {
		buf = appendU64(buf, uint64(d))
	}
	for _, s := range t.strides {
		buf = appendI64(buf, int64(s))
	}
	buf = appendU64(buf, uint64(t.offset))
	buf = appendU64(buf, uint64(payloadSize))
	payload := t.st.data[t.offset*t.st.dtype.Size() : t.offset*t.st.dtype.Size()+payloadSize]
	buf = append(buf, payload...)
	checksum := utils.Hash64(buf)
	buf = appendU64(buf, checksum)
	return buf, nil
}

// Load deserializes a tensor from a byte stream produced by Save.
func Load(data []byte) (*Tensor, error) {
	if len(data) < headerSize+8 {
		return nil, errors.New(errors.CodeCorruptData, "truncated tensor stream")
	}
	if string(data[:4]) != formatMagic {
		return nil, errors.New(errors.CodeCorruptData, "bad magic").
			WithField("magic", string(data[:4]))
	}
	pos := 4
	version := binary.LittleEndian.Uint16(data[pos:])
	pos += 2
	if version != formatVersion {
		return nil, errors.New(errors.CodeVersionMismatch, "unsupported format version").
			WithField("version", version)
	}
	dtypeCode := binary.LittleEndian.Uint16(data[pos:])
	pos += 2
	if int(dtypeCode) >= int(NumDTypes) {
		return nil, errors.New(errors.CodeCorruptData, "unknown dtype code").
			WithField("code", dtypeCode)
	}
	dtype := DType(dtypeCode)
	rank := int(binary.LittleEndian.Uint16(data[pos:]))
	pos += 2
	if rank > MaxRank {
		return nil, errors.New(errors.CodeCorruptData, "rank exceeds maximum").
			WithField("rank", rank)
	}
	need := headerSize + rank*16 + rank*8 + 16 + 8
	if len(data) < need {
		return nil, errors.New(errors.CodeCorruptData, "truncated header")
	}
	dims := make([]int, rank)
	for i := range dims {
		dims[i] = int(binary.LittleEndian.Uint64(data[pos:]))
		pos += 8
	}
	strides := make([]int, rank)
	for i := range strides {
		strides[i] = int(int64(binary.LittleEndian.Uint64(data[pos:])))
		pos += 8
	}
	offset := int(binary.LittleEndian.Uint64(data[pos:]))
	pos += 8
	payloadSize := int(binary.LittleEndian.Uint64(data[pos:]))
	pos += 8
	if len(data) < pos+payloadSize+8 {
		return nil, errors.New(errors.CodeCorruptData, "truncated payload")
	}
	storedChecksum := binary.LittleEndian.Uint64(data[pos+payloadSize:])
	computed := utils.Hash64(data[:pos+payloadSize])
	if storedChecksum != computed {
		return nil, errors.New(errors.CodeCorruptData, "checksum mismatch").
			WithField("stored", storedChecksum).WithField("computed", computed)
	}
	shape, err := NewShape(dims...)
	if err != nil {
		return nil, err
	}
	expectedNumel := shape.NumElements()
	if payloadSize != dtype.Size()*expectedNumel {
		return nil, errors.New(errors.CodeCorruptData, "payload size inconsistent with shape").
			WithField("payload", payloadSize).WithField("expected", dtype.Size()*expectedNumel)
	}
	st, err := NewStorage(dtype, expectedNumel)
	if err != nil {
		return nil, err
	}
	copy(st.data, data[pos:pos+payloadSize])
	return &Tensor{
		st:      st,
		offset:  offset,
		shape:   shape,
		strides: strides,
	}, nil
}

// WriteTo streams the serialized tensor to w.
func WriteTo(t *Tensor, w io.Writer) error {
	data, err := Save(t)
	if err != nil {
		return err
	}
	_, err = w.Write(data)
	return err
}

// ReadFrom reads a serialized tensor from r.
func ReadFrom(r io.Reader) (*Tensor, error) {
	header := make([]byte, 4)
	if _, err := io.ReadFull(r, header); err != nil {
		return nil, errors.Wrap(err, errors.CodeCorruptData, "magic read failed")
	}
	if string(header) != formatMagic {
		return nil, errors.New(errors.CodeCorruptData, "bad magic")
	}
	meta := make([]byte, 2+2+2)
	if _, err := io.ReadFull(r, meta); err != nil {
		return nil, errors.Wrap(err, errors.CodeCorruptData, "header read failed")
	}
	version := binary.LittleEndian.Uint16(meta[0:2])
	if version != formatVersion {
		return nil, errors.New(errors.CodeVersionMismatch, "unsupported format version")
	}
	dtypeCode := binary.LittleEndian.Uint16(meta[2:4])
	rank := int(binary.LittleEndian.Uint16(meta[4:6]))
	dims := make([]byte, rank*16)
	if _, err := io.ReadFull(r, dims); err != nil {
		return nil, errors.Wrap(err, errors.CodeCorruptData, "shape read failed")
	}
	shapeDims := make([]int, rank)
	strides := make([]int, rank)
	for i := 0; i < rank; i++ {
		shapeDims[i] = int(binary.LittleEndian.Uint64(dims[i*16 : i*16+8]))
		strides[i] = int(int64(binary.LittleEndian.Uint64(dims[i*16+8 : i*16+16])))
	}
	tail := make([]byte, 16)
	if _, err := io.ReadFull(r, tail); err != nil {
		return nil, errors.Wrap(err, errors.CodeCorruptData, "offset read failed")
	}
	offset := int(binary.LittleEndian.Uint64(tail[0:8]))
	payloadSize := int(binary.LittleEndian.Uint64(tail[8:16]))
	payload := make([]byte, payloadSize)
	if _, err := io.ReadFull(r, payload); err != nil {
		return nil, errors.Wrap(err, errors.CodeCorruptData, "payload read failed")
	}
	checksumBytes := make([]byte, 8)
	if _, err := io.ReadFull(r, checksumBytes); err != nil {
		return nil, errors.Wrap(err, errors.CodeCorruptData, "checksum read failed")
	}
	body := make([]byte, 0, headerSize+len(dims)+16+payloadSize)
	body = append(body, formatMagic...)
	body = appendU16(body, version)
	body = appendU16(body, uint16(dtypeCode))
	body = appendU16(body, uint16(rank))
	body = append(body, dims...)
	body = appendU64(body, uint64(offset))
	body = appendU64(body, uint64(payloadSize))
	body = append(body, payload...)
	stored := binary.LittleEndian.Uint64(checksumBytes)
	computed := utils.Hash64(body)
	if stored != computed {
		return nil, errors.New(errors.CodeCorruptData, "checksum mismatch")
	}
	if int(dtypeCode) >= int(NumDTypes) {
		return nil, errors.New(errors.CodeCorruptData, "unknown dtype code")
	}
	dtype := DType(dtypeCode)
	shape, err := NewShape(shapeDims...)
	if err != nil {
		return nil, err
	}
	st, err := NewStorage(dtype, shape.NumElements())
	if err != nil {
		return nil, err
	}
	copy(st.data, payload)
	return &Tensor{
		st:      st,
		offset:  offset,
		shape:   shape,
		strides: strides,
	}, nil
}

func appendU16(buf []byte, v uint16) []byte {
	return append(buf, byte(v), byte(v>>8))
}

func appendU64(buf []byte, v uint64) []byte {
	var tmp [8]byte
	binary.LittleEndian.PutUint64(tmp[:], v)
	return append(buf, tmp[:]...)
}

func appendI64(buf []byte, v int64) []byte {
	return appendU64(buf, uint64(v))
}

// ErrTruncated signals a truncated stream.
var ErrTruncated = errors.New(errors.CodeCorruptData, "truncated stream")
