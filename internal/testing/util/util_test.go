package util

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestGoldenCreatesFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "golden_test.txt")
	Golden(t, []byte("hello"), path)
}

func TestGoldenMatches(t *testing.T) {
	path := filepath.Join(t.TempDir(), "golden_match.txt")
	os.WriteFile(path, []byte("hello"), 0644)
	Golden(t, []byte("hello"), path)
}

func TestGoldenMismatch(t *testing.T) {
	path := filepath.Join(t.TempDir(), "golden_mismatch.txt")
	os.WriteFile(path, []byte("hello"), 0644)
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic")
		}
	}()
	Golden(t, []byte("world"), path)
}

func TestMustMarshal(t *testing.T) {
	data := MustMarshal(t, map[string]string{"a": "b"})
	if !bytes.Contains(data, []byte("a")) {
		t.Fatal("expected a in json")
	}
}

func TestMustUnmarshal(t *testing.T) {
	var v map[string]string
	MustUnmarshal(t, []byte(`{"a":"b"}`), &v)
	if v["a"] != "b" {
		t.Fatalf("unexpected: %v", v)
	}
}
