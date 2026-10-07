package util

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"testing"
)

// Golden compares output against a golden file.
func Golden(t *testing.T, got []byte, goldenPath string) {
	t.Helper()
	want, err := os.ReadFile(goldenPath)
	if os.IsNotExist(err) {
		if err := os.WriteFile(goldenPath, got, 0644); err != nil {
			t.Fatalf("write golden: %v", err)
		}
		return
	}
	if err != nil {
		t.Fatalf("read golden: %v", err)
	}
	if !bytes.Equal(got, want) {
		panic(fmt.Sprintf("golden mismatch.\ngot:\n%s\nwant:\n%s", got, want))
	}
}

// MustMarshal marshals v to JSON or fails the test.
func MustMarshal(t *testing.T, v interface{}) []byte {
	t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	return b
}

// MustUnmarshal unmarshals JSON or fails the test.
func MustUnmarshal(t *testing.T, data []byte, v interface{}) {
	t.Helper()
	if err := json.Unmarshal(data, v); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
}
