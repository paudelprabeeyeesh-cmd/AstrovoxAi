package crashreport

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func newReport(ts time.Time) *Report {
	return &Report{Version: "1.0.0", Timestamp: ts, Summary: "panic: test"}
}

func TestBuildReport(t *testing.T) {
	r := &Report{
		Version: "1.0.0", Timestamp: time.Now(),
		Summary: "panic: boom", Stack: "goroutine 1",
		Environment: map[string]string{"user_home": "[REDACTED]"},
	}
	out := string(r.BuildReport())
	for _, want := range []string{"Astrovox Crash Report", "1.0.0", "panic: boom", "goroutine 1", "[REDACTED]"} {
		if !contains(out, want) {
			t.Errorf("report missing %q:\n%s", want, out)
		}
	}
}

func contains(s, sub string) bool {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

func TestFileName(t *testing.T) {
	ts := time.Unix(0, 1700000000123456789)
	name := newReport(ts).FileName()
	if name != "crash-1700000000123456789.txt" {
		t.Errorf("got %q", name)
	}
}

func TestCapture(t *testing.T) {
	r := Capture("2.0.0", "boom", "stack trace")
	if r.Version != "2.0.0" {
		t.Error("version")
	}
	if r.Summary != "panic: boom" {
		t.Errorf("summary: %s", r.Summary)
	}
	// No real environment values must be recorded.
	for _, v := range r.Environment {
		if v == os.Getenv("PATH") || v == "/tmp" {
			t.Errorf("environment should be redacted, got %q", v)
		}
	}
}

func TestSaveAndPrune(t *testing.T) {
	dir := filepath.Join(os.TempDir(), "astrovox-crash-test")
	os.RemoveAll(dir)
	defer os.RemoveAll(dir)

	base := time.Unix(0, 1700000000000000000)
	for i := 0; i < 8; i++ {
		if _, err := Save(dir, newReport(base.Add(time.Duration(i)*time.Second))); err != nil {
			t.Fatal(err)
		}
	}
	// Retention must cap the number of stored reports.
	if got := Count(dir); got != RetainedMax {
		t.Errorf("expected %d retained, got %d", RetainedMax, got)
	}
}

func TestSaveValidation(t *testing.T) {
	if _, err := Save("", nil); err == nil {
		t.Error("expected empty dir error")
	}
	dir := filepath.Join(os.TempDir(), "astrovox-crash-valid")
	defer os.RemoveAll(dir)
	if _, err := Save(dir, nil); err == nil {
		t.Error("expected nil report error")
	}
}

func TestSaveWithProfile(t *testing.T) {
	dir := filepath.Join(os.TempDir(), "astrovox-crash-prof")
	os.RemoveAll(dir)
	defer os.RemoveAll(dir)
	r := newReport(time.Now())
	path, err := SaveWithProfile(dir, r, "1.0.0")
	if err != nil {
		t.Fatal(err)
	}
	if path == "" {
		t.Error("expected a path")
	}
	entries, _ := filepath.Glob(filepath.Join(dir, "crash-*heap.pprof"))
	if len(entries) != 1 {
		t.Errorf("expected a heap profile, got %v", entries)
	}
}

func TestSaveWithProfileEmptyVersion(t *testing.T) {
	dir := filepath.Join(os.TempDir(), "astrovox-crash-prof2")
	os.RemoveAll(dir)
	defer os.RemoveAll(dir)
	r := newReport(time.Now())
	// An empty version skips profile writing; the report must still land.
	path, err := SaveWithProfile(dir, r, "")
	if err != nil {
		t.Fatal(err)
	}
	if path == "" {
		t.Error("expected a path")
	}
	entries, _ := filepath.Glob(filepath.Join(dir, "crash-*heap.pprof"))
	if len(entries) != 0 {
		t.Error("profile should not be written for an empty version")
	}
}

func TestRedactedValue(t *testing.T) {
	if RedactedValue("secret-token") != redactedPlaceholder {
		t.Error("expected the redacted placeholder")
	}
}

func TestCountMissingDir(t *testing.T) {
	if got := Count(filepath.Join(os.TempDir(), "astrovox-crash-missing-xyz")); got != 0 {
		t.Errorf("expected 0 for a missing dir, got %d", got)
	}
}