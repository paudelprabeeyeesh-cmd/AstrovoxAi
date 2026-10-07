package main

import (
	"bytes"
	"os"
	"strings"
	"testing"
)

func TestMainInit(t *testing.T) {
	oldArgs := os.Args
	defer func() { os.Args = oldArgs }()
	os.Args = []string{"astrovox", "init", "./tmp"}
	oldStdout := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w
	main()
	w.Close()
	var buf bytes.Buffer
	buf.ReadFrom(r)
	os.Stdout = oldStdout
	if !strings.Contains(buf.String(), "Initialized project") {
		t.Fatalf("expected init output, got %s", buf.String())
	}
}
