package checkpoint

import (
	"encoding/binary"
	"hash/crc64"
	"os"
	"path/filepath"
	"testing"

	"github.com/astrovox/astrovox/internal/errors"
)

func sampleCheckpoint() *FileCheckpoint {
	return &FileCheckpoint{
		Version: FileFormatVersion,
		Model:   "mlp-demo",
		Parameters: []NamedTensor{
			{Name: "fc1.W", Shape: []int{2, 3}, Data: []float64{1, 2, 3, 4, 5, 6}},
			{Name: "fc1.b", Shape: []int{3}, Data: []float64{0.5, -0.25, 0}},
			{Name: "fc2.W", Shape: []int{3, 1}, Data: []float64{-1, 0, 1}},
		},
		Optimizer: &OptimizerState{
			Kind: "adam",
			Step: 7,
			Moments: map[string][]float64{
				"fc1.W": append(append([]float64{}, repeat(0.1, 6)...), repeat(0.01, 6)...),
				"fc1.b": append(append([]float64{}, repeat(0.1, 3)...), repeat(0.01, 3)...),
				"fc2.W": append(append([]float64{}, repeat(0.1, 3)...), repeat(0.01, 3)...),
			},
		},
		Metadata: map[string]string{"task": "regression", "seed": "42"},
	}
}

func repeat(v float64, n int) []float64 {
	out := make([]float64, n)
	for i := range out {
		out[i] = v
	}
	return out
}

func TestFileCheckpointRoundTrip(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "model.axck")
	cp := sampleCheckpoint()
	if err := WriteFile(path, cp); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	got, err := ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if got.Version != cp.Version || got.Model != cp.Model {
		t.Fatalf("header mismatch: %+v", got)
	}
	if len(got.Parameters) != 3 {
		t.Fatalf("parameter count = %d, want 3", len(got.Parameters))
	}
	// Parameters come back in name-sorted order.
	names := []string{"fc1.W", "fc1.b", "fc2.W"}
	for i, p := range got.Parameters {
		if p.Name != names[i] {
			t.Fatalf("parameter %d = %q, want %q", i, p.Name, names[i])
		}
		if len(p.Data) != len(cp.Parameters[i].Data) {
			t.Fatalf("parameter %s data length = %d, want %d", p.Name, len(p.Data), len(cp.Parameters[i].Data))
		}
		for j, v := range p.Data {
			if v != cp.Parameters[i].Data[j] {
				t.Fatalf("parameter %s data[%d] = %v, want %v", p.Name, j, v, cp.Parameters[i].Data[j])
			}
		}
	}
	if got.Optimizer == nil || got.Optimizer.Kind != "adam" || got.Optimizer.Step != 7 {
		t.Fatalf("optimizer state mismatch: %+v", got.Optimizer)
	}
	if len(got.Optimizer.Moments["fc1.W"]) != 12 {
		t.Fatalf("moment buffer length = %d, want 12", len(got.Optimizer.Moments["fc1.W"]))
	}
	if got.Metadata["seed"] != "42" {
		t.Fatalf("metadata = %v", got.Metadata)
	}
}

// TestWriteIsDeterministic: identical state produces byte-identical
// files, which is what makes checkpoints reproducible artifacts.
func TestWriteIsDeterministic(t *testing.T) {
	dir := t.TempDir()
	a := filepath.Join(dir, "a.axck")
	b := filepath.Join(dir, "b.axck")
	if err := WriteFile(a, sampleCheckpoint()); err != nil {
		t.Fatal(err)
	}
	if err := WriteFile(b, sampleCheckpoint()); err != nil {
		t.Fatal(err)
	}
	ba, err := os.ReadFile(a)
	if err != nil {
		t.Fatal(err)
	}
	bb, err := os.ReadFile(b)
	if err != nil {
		t.Fatal(err)
	}
	if len(ba) != len(bb) {
		t.Fatalf("file sizes differ: %d vs %d", len(ba), len(bb))
	}
	for i := range ba {
		if ba[i] != bb[i] {
			t.Fatalf("byte %d differs: %x vs %x", i, ba[i], bb[i])
		}
	}
}

// TestCorruptionIsDetected: any single-byte change anywhere in the file
// must be refused, never silently loaded as valid data.
func TestCorruptionIsDetected(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "model.axck")
	if err := WriteFile(path, sampleCheckpoint()); err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	for _, pos := range []int{0, 3, 11, 12, 20, len(raw) / 2, len(raw) - 9, len(raw) - 8} {
		corrupt := append([]byte(nil), raw...)
		corrupt[pos] ^= 0xff
		bad := filepath.Join(dir, "corrupt.axck")
		if err := os.WriteFile(bad, corrupt, 0o644); err != nil {
			t.Fatal(err)
		}
		if _, err := ReadFile(bad); err == nil {
			t.Fatalf("corruption at byte %d was loaded without error", pos)
		} else if errors.CodeOf(err) != errors.CodeCorruptData && errors.CodeOf(err) != errors.CodeVersionMismatch {
			t.Fatalf("corruption at %d: unexpected error class %v", pos, errors.CodeOf(err))
		}
		if _, err := Inspect(bad); err == nil {
			t.Fatalf("Inspect accepted corruption at byte %d", pos)
		}
	}
}

// TestTruncatedFileIsRefused: a torn write (power loss mid-flush) must
// fail closed, not yield a partial checkpoint.
func TestTruncatedFileIsRefused(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "model.axck")
	if err := WriteFile(path, sampleCheckpoint()); err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	for _, cut := range []int{0, 4, 12, len(raw) / 2, len(raw) - 9} {
		bad := filepath.Join(dir, "torn.axck")
		if err := os.WriteFile(bad, raw[:cut], 0o644); err != nil {
			t.Fatal(err)
		}
		if _, err := ReadFile(bad); err == nil {
			t.Fatalf("a %d-byte truncation was loaded without error", cut)
		}
		if _, err := Inspect(bad); err == nil {
			t.Fatalf("Inspect accepted a %d-byte truncation", cut)
		}
	}
}

// TestInterruptedWriteLeavesPreviousCheckpoint: simulating a crash
// after the temp file is written but before the rename, the destination
// must still hold the previous good checkpoint, and no stray partial
// file may be mistaken for one.
func TestInterruptedWriteLeavesPreviousCheckpoint(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "model.axck")
	if err := WriteFile(path, sampleCheckpoint()); err != nil {
		t.Fatal(err)
	}
	good, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	// A crash mid-write leaves the temp file behind.
	tmp := filepath.Join(dir, ".astrovox-ckpt-crashed.tmp")
	if err := os.WriteFile(tmp, good[:len(good)/2], 0o644); err != nil {
		t.Fatal(err)
	}
	got, err := ReadFile(path)
	if err != nil {
		t.Fatalf("previous checkpoint was damaged by an interrupted write: %v", err)
	}
	if len(got.Parameters) != 3 {
		t.Fatalf("previous checkpoint lost parameters: %d", len(got.Parameters))
	}
	// The interrupted temp file is not a valid checkpoint.
	if _, err := ReadFile(tmp); err == nil {
		t.Fatal("a torn temp file was accepted as a checkpoint")
	}
}

// TestFutureVersionIsRefused: a file from a newer writer must fail with
// a version error, not be interpreted under older rules.
func TestFutureVersionIsRefused(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "future.axck")
	body := append([]byte(nil), []byte("AXCK")...)
	body = binary.LittleEndian.AppendUint32(body, FileFormatVersion+1)
	body = binary.LittleEndian.AppendUint32(body, 2)
	body = append(body, '{', '}')
	body = binary.LittleEndian.AppendUint64(body, crc64.Checksum(body, crcTable))
	if err := os.WriteFile(path, body, 0o644); err != nil {
		t.Fatal(err)
	}
	_, err := ReadFile(path)
	if err == nil {
		t.Fatal("a newer-format file was accepted")
	}
	if errors.CodeOf(err) != errors.CodeVersionMismatch {
		t.Fatalf("error code = %v, want VERSION_MISMATCH", errors.CodeOf(err))
	}
}

// TestHeaderShapePayloadMismatchIsRefused: a header claiming a shape the
// payload cannot fill must fail during validation.
func TestHeaderShapePayloadMismatchIsRefused(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "liar.axck")
	cp := sampleCheckpoint()
	cp.Parameters[0].Shape = []int{2, 4} // claims 8 elements, has 6
	if err := WriteFile(path, cp); err != nil {
		// Rejected at write time: even better.
		return
	}
	if _, err := ReadFile(path); err == nil {
		t.Fatal("a shape/data mismatch was written and read back")
	}
}

func TestValidationRejectsBadState(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "bad.axck")

	// Empty model name.
	cp := sampleCheckpoint()
	cp.Model = ""
	if err := WriteFile(path, cp); err == nil {
		t.Fatal("an empty model name was accepted")
	}
	// Duplicate tensor names.
	cp = sampleCheckpoint()
	cp.Parameters = append(cp.Parameters, cp.Parameters[0])
	if err := WriteFile(path, cp); err == nil {
		t.Fatal("duplicate tensor names were accepted")
	}
	// Optimizer moment for an unknown parameter.
	cp = sampleCheckpoint()
	cp.Optimizer.Moments["nope"] = []float64{1}
	if err := WriteFile(path, cp); err == nil {
		t.Fatal("an unknown optimizer moment was accepted")
	}
	// Empty optimizer moment buffer.
	cp = sampleCheckpoint()
	cp.Optimizer.Moments["fc1.b"] = nil
	if err := WriteFile(path, cp); err == nil {
		t.Fatal("an empty moment buffer was accepted")
	}
	// Wrong version on write.
	cp = sampleCheckpoint()
	cp.Version = FileFormatVersion + 1
	if err := WriteFile(path, cp); err == nil {
		t.Fatal("a future version was accepted for writing")
	}
}

func TestInspectDoesNotMaterializePayload(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "model.axck")
	if err := WriteFile(path, sampleCheckpoint()); err != nil {
		t.Fatal(err)
	}
	cp, err := Inspect(path)
	if err != nil {
		t.Fatalf("Inspect: %v", err)
	}
	if cp.Model != "mlp-demo" || len(cp.Parameters) != 3 {
		t.Fatalf("inspected header = %+v", cp)
	}
	for _, p := range cp.Parameters {
		if p.Data != nil {
			t.Fatalf("Inspect materialized data for %s", p.Name)
		}
	}
	// Not-found is a typed error.
	if _, err := Inspect(filepath.Join(dir, "missing.axck")); errors.CodeOf(err) != errors.CodeNotFound {
		t.Fatalf("missing file error code = %v, want NOT_FOUND", errors.CodeOf(err))
	}
}
