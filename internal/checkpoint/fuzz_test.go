package checkpoint

import (
	"os"
	"testing"

	"github.com/astrovox/astrovox/internal/errors"
)

// validCheckpointBytes builds a real checkpoint and returns its bytes as
// the fuzz seed.
func validCheckpointBytes() []byte {
	cp := &FileCheckpoint{
		Version: FileFormatVersion,
		Model:   "fuzz",
		Parameters: []NamedTensor{
			{Name: "w", Shape: []int{2, 2}, Data: []float64{1, 2, 3, 4}},
		},
	}
	dir, _ := os.MkdirTemp("", "fuzz-seed-*")
	defer os.RemoveAll(dir)
	path := dir + "/seed.axck"
	if err := WriteFile(path, cp); err != nil {
		panic(err)
	}
	data, err := osReadFile(path)
	if err != nil {
		panic(err)
	}
	return data
}

// osReadFile reads file bytes.
func osReadFile(path string) ([]byte, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	return data, nil
}

// putBytes writes data to path for fuzz input placement.
func putBytes(path string, data []byte) error {
	fh, err := os.Create(path)
	if err != nil {
		return err
	}
	if _, err := fh.Write(data); err != nil {
		fh.Close()
		return err
	}
	return fh.Close()
}

// isTyped reports whether err carries an engine error code, so the fuzz
// target catches string-only or bare errors too.
func isTyped(err error) bool { return errors.CodeOf(err) != errors.CodeUnknown }

// FuzzCheckpointDecode feeds arbitrary bytes to the checkpoint reader.
// The reader must never panic: corrupted files are attacker-controlled
// input, and a panic in a persistence path is a denial-of-service bug.
// Every failure must be a typed error.
func FuzzCheckpointDecode(f *testing.F) {
	// Seed corpus: valid file, truncated, magic-corrupted, version-flipped.
	valid := string(validCheckpointBytes())
	f.Add(valid)
	f.Add(valid[:len(valid)/2])
	f.Add(string(append(append([]byte(nil), valid[:8]...), 0xff)))
	f.Add("AXCK")
	f.Add("")
	f.Fuzz(func(t *testing.T, data string) {
		path := t.TempDir() + "/fuzz.axck"
		if err := putBytes(path, []byte(data)); err != nil {
			t.Skip()
		}
		// Neither read path may panic.
		if _, err := ReadFile(path); err != nil {
			if !isTyped(err) {
				t.Fatalf("untyped error: %v", err)
			}
		}
		if _, err := Inspect(path); err != nil {
			if !isTyped(err) {
				t.Fatalf("untyped inspect error: %v", err)
			}
		}
	})
}
