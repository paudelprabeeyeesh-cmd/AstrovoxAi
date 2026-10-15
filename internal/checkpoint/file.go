package checkpoint

import (
	"encoding/binary"
	"encoding/json"
	"hash/crc64"
	"math"
	"os"
	"path/filepath"
	"sort"

	"github.com/astrovox/astrovox/internal/errors"
)

// FileFormatVersion is the on-disk checkpoint layout version. It is part
// of the file contract: a file written by a newer version is refused
// with CodeVersionMismatch rather than partially interpreted, and older
// versions are refused the same way unless a migration is implemented.
const FileFormatVersion = 1

// fileMagic identifies an Astrovox file checkpoint. The version follows
// as a uint32, then a uint32 header length, then the header JSON.
var fileMagic = [4]byte{'A', 'X', 'C', 'K'}

// NamedTensor is one parameter tensor in a file checkpoint.
type NamedTensor struct {
	Name  string
	Shape []int
	Data  []float64
}

// OptimizerState persists optimizer state next to the parameters, so a
// restored run continues with its moment estimates instead of restarting
// them. Kind names the optimizer; Moments maps a parameter name to its
// moment buffers in that optimizer's natural order (SGD: [velocity];
// Adam: [m, v]).
type OptimizerState struct {
	Kind    string
	Step    int64
	Moments map[string][]float64
}

// FileCheckpoint is the durable, versioned representation of a training
// state: parameters, optimizer state, and free-form metadata.
type FileCheckpoint struct {
	Version    int
	Model      string
	Parameters []NamedTensor
	Optimizer  *OptimizerState
	Metadata   map[string]string
}

// fileHeader is the JSON header. Tensor payloads follow the header in
// name-sorted order so the file is byte-for-byte deterministic for the
// same state.
type fileHeader struct {
	Version   int                `json:"version"`
	Model     string             `json:"model"`
	Metadata  map[string]string  `json:"metadata,omitempty"`
	Optimizer *OptimizerState    `json:"optimizer,omitempty"`
	Tensors   []fileTensorHeader `json:"tensors"`
}

type fileTensorHeader struct {
	Name   string `json:"name"`
	Shape  []int  `json:"shape"`
	Offset int64  `json:"offset"`
	Length int64  `json:"length"`
}

var crcTable = crc64.MakeTable(crc64.ECMA)

// WriteFile writes cp to path atomically: the payload is written to a
// temporary file in the same directory, flushed to disk, and renamed
// over the destination. An interrupted write therefore leaves the
// previous checkpoint intact and a partial temp file behind, never a
// truncated checkpoint at path.
//
// Durability note: the rename is atomic on NTFS, APFS, and ext4. The
// directory entry is flushed afterwards where the platform supports
// directory fsync; on platforms where it does not, the data blocks are
// durable but the rename may not survive an immediate power loss. This
// is a filesystem property, not a property this package can add.
func WriteFile(path string, cp *FileCheckpoint) error {
	if path == "" {
		return errors.New(errors.CodeInvalidArgument, "empty checkpoint path")
	}
	if cp == nil {
		return errors.New(errors.CodeInvalidArgument, "nil checkpoint")
	}
	if cp.Version != FileFormatVersion {
		return errors.New(errors.CodeVersionMismatch,
			"checkpoint version does not match the writer").
			WithField("got", cp.Version).WithField("want", FileFormatVersion)
	}
	if err := validate(cp); err != nil {
		return err
	}

	// Deterministic tensor order: sort by name.
	tensors := append([]NamedTensor(nil), cp.Parameters...)
	sort.Slice(tensors, func(i, j int) bool { return tensors[i].Name < tensors[j].Name })

	hdr := fileHeader{
		Version:   FileFormatVersion,
		Model:     cp.Model,
		Metadata:  cp.Metadata,
		Optimizer: cp.Optimizer,
		Tensors:   make([]fileTensorHeader, 0, len(tensors)),
	}
	var payload []byte
	var offset int64
	for _, t := range tensors {
		n := numel(t.Shape)
		if int64(len(t.Data)) != n {
			return errors.New(errors.CodeShapeMismatch,
				"tensor data length does not match its shape").
				WithField("name", t.Name).
				WithField("data_len", len(t.Data)).
				WithField("shape_numel", n)
		}
		hdr.Tensors = append(hdr.Tensors, fileTensorHeader{
			Name: t.Name, Shape: t.Shape, Offset: offset, Length: n,
		})
		buf := make([]byte, 8*n)
		for i, v := range t.Data {
			binary.LittleEndian.PutUint64(buf[i*8:], bitsOf(v))
		}
		payload = append(payload, buf...)
		offset += n
	}

	hdrBytes, err := json.Marshal(hdr)
	if err != nil {
		return errors.Wrap(err, errors.CodeInternal, "marshal checkpoint header")
	}

	var body []byte
	body = append(body, fileMagic[:]...)
	body = binary.LittleEndian.AppendUint32(body, FileFormatVersion)
	body = binary.LittleEndian.AppendUint32(body, uint32(len(hdrBytes)))
	body = append(body, hdrBytes...)
	body = append(body, payload...)
	body = binary.LittleEndian.AppendUint64(body, crc64.Checksum(body, crcTable))

	dir := filepath.Dir(path)
	tmp, err := os.CreateTemp(dir, ".astrovox-ckpt-*.tmp")
	if err != nil {
		return errors.Wrap(err, errors.CodeInternal, "create temp checkpoint")
	}
	tmpName := tmp.Name()
	if _, err := tmp.Write(body); err != nil {
		tmp.Close()
		os.Remove(tmpName)
		return errors.Wrap(err, errors.CodeInternal, "write temp checkpoint")
	}
	if err := tmp.Sync(); err != nil {
		tmp.Close()
		os.Remove(tmpName)
		return errors.Wrap(err, errors.CodeInternal, "fsync temp checkpoint")
	}
	if err := tmp.Close(); err != nil {
		os.Remove(tmpName)
		return errors.Wrap(err, errors.CodeInternal, "close temp checkpoint")
	}
	// Best-effort directory sync so the rename itself is durable where
	// the platform supports it; failures are not fatal because the file
	// data is already flushed.
	if d, err := os.Open(dir); err == nil {
		_ = d.Sync()
		d.Close()
	}
	if err := os.Rename(tmpName, path); err != nil {
		os.Remove(tmpName)
		return errors.Wrap(err, errors.CodeInternal, "rename checkpoint into place")
	}
	return nil
}

// ReadFile loads and fully validates a checkpoint written by WriteFile:
// version, header structure, checksum, and tensor shapes against the
// payload. Any mismatch is an error, so a corrupted file is refused
// instead of yielding a partially-populated checkpoint.
func ReadFile(path string) (*FileCheckpoint, error) {
	if path == "" {
		return nil, errors.New(errors.CodeInvalidArgument, "empty checkpoint path")
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, errors.Wrap(err, errors.CodeNotFound, "checkpoint not found")
		}
		return nil, errors.Wrap(err, errors.CodeInternal, "read checkpoint")
	}
	hdr, payload, err := parse(raw)
	if err != nil {
		return nil, err
	}

	cp := &FileCheckpoint{
		Version:   hdr.Version,
		Model:     hdr.Model,
		Metadata:  hdr.Metadata,
		Optimizer: hdr.Optimizer,
	}
	for _, th := range hdr.Tensors {
		if th.Length < 0 || th.Offset < 0 {
			return nil, errors.New(errors.CodeCorruptData,
				"tensor range is negative").
				WithField("name", th.Name)
		}
		// Offsets and lengths in the header are element counts; the
		// payload is 8 bytes per element.
		byteEnd := 8 * (th.Offset + th.Length)
		if byteEnd > int64(len(payload)) {
			return nil, errors.New(errors.CodeCorruptData,
				"tensor range exceeds the payload").
				WithField("name", th.Name).
				WithField("offset", th.Offset).
				WithField("length", th.Length).
				WithField("payload_len", len(payload))
		}
		if numel(th.Shape) != th.Length {
			return nil, errors.New(errors.CodeShapeMismatch,
				"tensor shape disagrees with the payload length").
				WithField("name", th.Name).
				WithField("shape_numel", numel(th.Shape)).
				WithField("length", th.Length)
		}
		buf := payload[8*th.Offset : byteEnd]
		data := make([]float64, th.Length)
		for i := range data {
			data[i] = fromBits(binary.LittleEndian.Uint64(buf[i*8:]))
		}
		cp.Parameters = append(cp.Parameters, NamedTensor{Name: th.Name, Shape: th.Shape, Data: data})
	}
	if err := validate(cp); err != nil {
		return nil, err
	}
	return cp, nil
}

// Inspect reads the header only, so a caller can examine a checkpoint's
// model, version, tensor names, and shapes without materializing the
// payload. The checksum is still verified: inspecting a corrupt file
// must fail loudly.
func Inspect(path string) (*FileCheckpoint, error) {
	if path == "" {
		return nil, errors.New(errors.CodeInvalidArgument, "empty checkpoint path")
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, errors.Wrap(err, errors.CodeNotFound, "checkpoint not found")
		}
		return nil, errors.Wrap(err, errors.CodeInternal, "read checkpoint")
	}
	hdr, _, err := parse(raw)
	if err != nil {
		return nil, err
	}
	cp := &FileCheckpoint{
		Version:   hdr.Version,
		Model:     hdr.Model,
		Metadata:  hdr.Metadata,
		Optimizer: hdr.Optimizer,
	}
	for _, th := range hdr.Tensors {
		cp.Parameters = append(cp.Parameters, NamedTensor{Name: th.Name, Shape: th.Shape})
	}
	return cp, nil
}

// parse verifies the framing and checksum and returns the header plus
// the payload. It is the single choke point every read path goes
// through, so corruption detection cannot be bypassed.
func parse(raw []byte) (*fileHeader, []byte, error) {
	if len(raw) < 4+4+4+8 {
		return nil, nil, errors.New(errors.CodeCorruptData, "checkpoint too short")
	}
	if [4]byte{raw[0], raw[1], raw[2], raw[3]} != fileMagic {
		return nil, nil, errors.New(errors.CodeCorruptData, "bad checkpoint magic")
	}
	version := binary.LittleEndian.Uint32(raw[4:8])
	if version != FileFormatVersion {
		return nil, nil, errors.New(errors.CodeVersionMismatch,
			"checkpoint format version unsupported").
			WithField("got", version).WithField("want", FileFormatVersion)
	}
	hdrLen := binary.LittleEndian.Uint32(raw[8:12])
	if int64(hdrLen) > int64(len(raw))-(4+4+4+8) {
		return nil, nil, errors.New(errors.CodeCorruptData, "checkpoint header length exceeds the file")
	}
	hdrStart := 12
	hdrEnd := hdrStart + int(hdrLen)
	payloadEnd := len(raw) - 8
	if payloadEnd < hdrEnd {
		return nil, nil, errors.New(errors.CodeCorruptData, "checkpoint payload is truncated")
	}
	wantSum := binary.LittleEndian.Uint64(raw[payloadEnd:])
	gotSum := crc64.Checksum(raw[:payloadEnd], crcTable)
	if gotSum != wantSum {
		return nil, nil, errors.New(errors.CodeCorruptData,
			"checkpoint checksum mismatch: the file was truncated or modified").
			WithField("want", wantSum).WithField("got", gotSum)
	}
	var hdr fileHeader
	if err := json.Unmarshal(raw[hdrStart:hdrEnd], &hdr); err != nil {
		return nil, nil, errors.Wrap(err, errors.CodeCorruptData, "decode checkpoint header")
	}
	return &hdr, raw[hdrEnd:payloadEnd], nil
}

// validate checks the structural invariants that both writing and
// loading must uphold: unique names, matching shape/data lengths, and a
// consistent optimizer state.
func validate(cp *FileCheckpoint) error {
	if cp.Model == "" {
		return errors.New(errors.CodeInvalidArgument, "checkpoint model name is empty")
	}
	seen := map[string]bool{}
	for _, t := range cp.Parameters {
		if t.Name == "" {
			return errors.New(errors.CodeInvalidArgument, "tensor name is empty")
		}
		if seen[t.Name] {
			return errors.New(errors.CodeInvalidArgument, "duplicate tensor name").
				WithField("name", t.Name)
		}
		seen[t.Name] = true
		if len(t.Shape) == 0 {
			return errors.New(errors.CodeInvalidArgument, "tensor shape is empty").
				WithField("name", t.Name)
		}
		for _, d := range t.Shape {
			if d <= 0 {
				return errors.New(errors.CodeShapeMismatch, "tensor shape has a non-positive dim").
					WithField("name", t.Name)
			}
		}
	}
	if cp.Optimizer != nil {
		for name, m := range cp.Optimizer.Moments {
			if !seen[name] {
				return errors.New(errors.CodeInvalidArgument,
					"optimizer moment references an unknown parameter").
					WithField("name", name)
			}
			if len(m) == 0 {
				return errors.New(errors.CodeInvalidArgument,
					"optimizer moment buffer is empty").
					WithField("name", name)
			}
		}
	}
	return nil
}

// numel returns the element count of a shape.
func numel(shape []int) int64 {
	n := int64(1)
	for _, d := range shape {
		n *= int64(d)
	}
	return n
}

// bitsOf and fromBits encode float64 payloads as little-endian IEEE-754,
// platform-independent regardless of the host's endianness.
func bitsOf(f float64) uint64   { return math.Float64bits(f) }
func fromBits(b uint64) float64 { return math.Float64frombits(b) }
