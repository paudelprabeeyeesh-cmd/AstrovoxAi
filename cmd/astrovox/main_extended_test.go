package main_test

import (
	"bytes"
	"flag"
	"strings"
	"testing"

	"github.com/astrovox/astrovox/pkg/cli"
)

func TestMainCLIInit(t *testing.T) {
	var buf bytes.Buffer
	c := cli.NewCLI("astrovox", "1.0.0")
	c.AddCommand(&cli.Command{
		Name:        "init",
		Description: "initialize project",
		Action: func(args []string) error {
			buf.WriteString("initialized")
			return nil
		},
	})
	if err := c.Run([]string{"init"}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(buf.String(), "initialized") {
		t.Fatal("expected initialized")
	}
}

func TestMainCLIUnknownCommand(t *testing.T) {
	c := cli.NewCLI("astrovox", "1.0.0")
	err := c.Run([]string{"unknown"})
	if err == nil || !strings.Contains(err.Error(), "unknown command") {
		t.Fatalf("expected unknown command error, got %v", err)
	}
}

func TestMainCLIHelp(t *testing.T) {
	c := cli.NewCLI("astrovox", "1.0.0")
	c.AddCommand(&cli.Command{Name: "init", Description: "init"})
	c.AddCommand(&cli.Command{Name: "train", Description: "train"})
	if err := c.Run([]string{}); err != nil {
		t.Fatalf("help should not error: %v", err)
	}
}

func TestMainCLIMultipleCommands(t *testing.T) {
	c := cli.NewCLI("astrovox", "1.0.0")
	order := []string{}
	c.AddCommand(&cli.Command{
		Name: "first",
		Action: func(args []string) error {
			order = append(order, "first")
			return nil
		},
	})
	c.AddCommand(&cli.Command{
		Name: "second",
		Action: func(args []string) error {
			order = append(order, "second")
			return nil
		},
	})
	c.Run([]string{"first"})
	c.Run([]string{"second"})
	if len(order) != 2 || order[0] != "first" || order[1] != "second" {
		t.Fatalf("unexpected order: %v", order)
	}
}

func TestMainCLIWithFlags(t *testing.T) {
	c := cli.NewCLI("astrovox", "1.0.0")
	received := ""
	c.AddCommand(&cli.Command{
		Name:   "cmd",
		Flags:  flag.NewFlagSet("cmd", flag.ContinueOnError),
		Action: func(args []string) error { received = strings.Join(args, ","); return nil },
	})
	fs := flag.NewFlagSet("cmd", flag.ContinueOnError)
	fs.String("name", "default", "name")
	if err := c.Run([]string{"cmd", "-name", "test"}); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	_ = received
}

func TestMainCLIEnvFlags(t *testing.T) {
	env := cli.ParseEnvFlags("ASTROVOX_")
	if len(env) == 0 {
		t.Fatal("expected some env flags")
	}
}

func TestMainCLIColoredWriter(t *testing.T) {
	var buf bytes.Buffer
	cw := cli.NewColoredWriter(&buf)
	cw.Info("info")
	cw.Warn("warn")
	cw.Error("error")
	cw.Success("success")
	if buf.Len() == 0 {
		t.Fatal("expected output")
	}
}

func TestMainCLIShellCompletion(t *testing.T) {
	sc := cli.NewShellCompletion()
	bash := sc.ForBash()
	if !strings.Contains(bash, "astrovox") {
		t.Fatal("expected bash completion")
	}
}

func TestMainCLIJSONOutput(t *testing.T) {
	var buf bytes.Buffer
	data := map[string]string{"key": "value"}
	if err := cli.JSONOutput(&buf, data); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(buf.String(), "key") {
		t.Fatal("expected key in output")
	}
}

func TestMainCLITimedAction(t *testing.T) {
	err := cli.TimedAction("test", func() error { return nil })
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestMainCLIRuntimeInfo(t *testing.T) {
	info := cli.RuntimeInfo()
	if info["os"] == "" || info["arch"] == "" {
		t.Fatal("expected runtime info")
	}
}

func TestMainCLIEnvWithPrefix(t *testing.T) {
	env := cli.EnvWithPrefix("ASTROVOX_")
	_ = env
}

func TestMainCLIProgressBar(t *testing.T) {
	var buf bytes.Buffer
	pb := cli.NewProgressBar(10, &buf)
	pb.SetProgress(5)
	if !strings.Contains(buf.String(), "50%") {
		t.Fatalf("expected 50%% in output")
	}
}

func TestMainCLICommandConfig(t *testing.T) {
	cmd := cli.CommandConfig{
		Name:        "test",
		Description: "test command",
		Flags:       map[string]string{"flag": "value"},
	}
	if cmd.Name != "test" {
		t.Fatalf("unexpected name")
	}
}

func TestMainCLIPrintf(t *testing.T) {
	c := cli.NewCLI("astrovox", "1.0.0")
	c.Printf("hello %s", "world")
}

func TestMainCLIFatalf(t *testing.T) {
	c := cli.NewCLI("astrovox", "1.0.0")
	defer func() {
		if r := recover(); r == nil {
			t.Fatal("expected panic from Fatalf")
		}
	}()
	c.Fatalf("test error")
}

func TestMainCLIShellCompletionZsh(t *testing.T) {
	sc := cli.NewShellCompletion()
	zsh := sc.ForZsh()
	if !strings.Contains(zsh, "astrovox") {
		t.Fatal("expected zsh completion")
	}
}
