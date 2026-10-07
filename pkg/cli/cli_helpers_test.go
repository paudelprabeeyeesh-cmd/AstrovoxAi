package cli

import "testing"

func TestNewCLI(t *testing.T) {
	c := NewCLI("astrovox", "1.0.0")
	if c.name != "astrovox" || c.version != "1.0.0" {
		t.Fatal("unexpected cli")
	}
}

func TestAddCommand(t *testing.T) {
	c := NewCLI("astrovox", "1.0.0")
	cmd := &Command{Name: "init", Description: "initialize"}
	c.AddCommand(cmd)
	if len(c.commands) != 1 {
		t.Fatalf("expected 1 command, got %d", len(c.commands))
	}
}

func TestRunUnknownCommand(t *testing.T) {
	c := NewCLI("astrovox", "1.0.0")
	err := c.Run([]string{"unknown"})
	if err == nil || !strings.Contains(err.Error(), "unknown command") {
		t.Fatalf("expected unknown command error, got %v", err)
	}
}

func TestPrintf(t *testing.T) {
	c := NewCLI("astrovox", "1.0.0")
	c.Printf("hello %s", "world")
	c.out.Flush()
}

func TestParseEnvFlags(t *testing.T) {
	os.Setenv("ASTROVOX_TEST", "value")
	defer os.Unsetenv("ASTROVOX_TEST")
	env := ParseEnvFlags("ASTROVOX_")
	if env["ASTROVOX_TEST"] != "value" {
		t.Fatalf("expected env var, got %v", env)
	}
}

func TestProgressBar(t *testing.T) {
	var buf strings.Builder
	pb := NewProgressBar(10, &buf)
	pb.SetProgress(5)
	if !strings.Contains(buf.String(), "50%") {
		t.Fatalf("expected 50%% in output, got %s", buf.String())
	}
}

func TestProgressBarComplete(t *testing.T) {
	var buf strings.Builder
	pb := NewProgressBar(10, &buf)
	pb.SetProgress(10)
	if !strings.Contains(buf.String(), "100%") {
		t.Fatalf("expected 100%% in output")
	}
}

func TestColoredWriter(t *testing.T) {
	var buf strings.Builder
	cw := NewColoredWriter(&buf)
	cw.Info("test")
	cw.Warn("test")
	cw.Error("test")
	cw.Success("test")
	if buf.Len() == 0 {
		t.Fatal("expected output")
	}
}

func TestShellCompletionBash(t *testing.T) {
	sc := NewShellCompletion()
	bash := sc.ForBash()
	if !strings.Contains(bash, "astrovox") {
		t.Fatal("expected bash completion")
	}
}

func TestShellCompletionZsh(t *testing.T) {
	sc := NewShellCompletion()
	zsh := sc.ForZsh()
	if !strings.Contains(zsh, "astrovox") {
		t.Fatal("expected zsh completion")
	}
}

func TestJSONOutput(t *testing.T) {
	var buf strings.Builder
	data := map[string]string{"key": "value"}
	if err := JSONOutput(&buf, data); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(buf.String(), "key") {
		t.Fatal("expected key in output")
	}
}

func TestTimedActionSuccess(t *testing.T) {
	err := TimedAction("test", func() error { return nil })
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestTimedActionFailure(t *testing.T) {
	err := TimedAction("test", func() error { return fmt.Errorf("fail") })
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestRuntimeInfo(t *testing.T) {
	info := RuntimeInfo()
	if info["os"] == "" || info["arch"] == "" {
		t.Fatal("expected runtime info")
	}
}

func TestEnvWithPrefix(t *testing.T) {
	os.Setenv("PREFIX_TEST", "value")
	defer os.Unsetenv("PREFIX_TEST")
	env := EnvWithPrefix("PREFIX_")
	if env["PREFIX_TEST"] != "value" {
		t.Fatalf("expected env var")
	}
}
