package cli

import (
	"bufio"
	"bytes"
	"strings"
	"testing"
)

func TestCLIRunInit(t *testing.T) {
	c := NewCLI("astrovox", "0.1.0")
	var out bytes.Buffer
	c.out = bufio.NewWriter(&out)
	c.err = bufio.NewWriter(&out)

	cmd := &Command{
		Name:        "init",
		Description: "Initialize a new project",
		Action: func(args []string) error {
			c.Printf("initialized %s\n", ".")
			return nil
		},
	}
	c.AddCommand(cmd)

	if err := c.Run([]string{"init"}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(out.String(), "initialized") {
		t.Fatalf("expected output to contain 'initialized', got %s", out.String())
	}
}

func TestCLIRunUnknown(t *testing.T) {
	c := NewCLI("astrovox", "0.1.0")
	err := c.Run([]string{"unknown"})
	if err == nil {
		t.Fatal("expected error for unknown command")
	}
}
