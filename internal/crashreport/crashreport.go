// Package crashreport captures panics into structured, redacted crash
// reports suitable for local inspection or opt-in upload.
package crashreport

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime/pprof"
	"time"
)

// RetainedMin is the minimum number of reports retained.
const RetainedMin = 3

// RetainedMax is the number of reports retained after pruning.
const RetainedMax = 5

const redactedPlaceholder = "[REDACTED]"

// Report is a captured crash.
type Report struct {
	Version     string
	Timestamp   time.Time
	Summary     string
	Stack       string
	Goroutine   string
	Environment map[string]string
	Payload     []byte
}

// RedactedValue hides a value that may hold secrets.
func RedactedValue(v string) string { return redactedPlaceholder }

// BuildReport renders a report as human-readable text.
func (r *Report) BuildReport() []byte {
	out := fmt.Sprintf("=== Astrovox Crash Report ===\nversion: %s\ntime: %s\n--- summary ---\n%s\n--- stack ---\n%s\n",
		r.Version, r.Timestamp.Format(time.RFC3339), r.Summary, r.Stack)
	if r.Goroutine != "" {
		out += "--- goroutine ---\n" + r.Goroutine + "\n"
	}
	if len(r.Environment) > 0 {
		out += "--- environment (redacted) ---\n"
		for k, v := range r.Environment {
			out += fmt.Sprintf("%s=%s\n", k, v)
		}
	}
	if len(r.Payload) > 0 {
		out += "--- payload ---\n" + string(r.Payload) + "\n"
	}
	return []byte(out)
}

// FileName returns the on-disk file name for the report.
func (r *Report) FileName() string {
	return fmt.Sprintf("crash-%d.txt", r.Timestamp.UnixNano())
}

// Capture builds a report from a recovered value.
func Capture(version string, recovered interface{}, stack string) *Report {
	return &Report{
		Version:   version,
		Timestamp: time.Now(),
		Summary:   fmt.Sprintf("panic: %v", recovered),
		Stack:     stack,
		Environment: map[string]string{
			// Never record the process environment: it routinely holds
			// tokens and keys. Report only stable hints.
			"user_home": redactedPlaceholder,
			"tmp":       redactedPlaceholder,
		},
	}
}

// Save writes the report to dir and prunes old reports, keeping at most
// RetainedMax files.
func Save(dir string, r *Report) (string, error) {
	if dir == "" || r == nil {
		return "", fmt.Errorf("dir and report are required")
	}
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return "", err
	}
	path := filepath.Join(dir, r.FileName())
	if err := os.WriteFile(path, r.BuildReport(), 0o600); err != nil {
		return "", err
	}
	if err := prune(dir); err != nil {
		return path, err
	}
	return path, nil
}

// SaveWithProfile additionally writes a heap profile next to the report.
func SaveWithProfile(dir string, r *Report, version string) (string, error) {
	path, err := Save(dir, r)
	if err != nil {
		return "", err
	}
	if dir == "" || version == "" {
		return path, nil
	}
	profPath := filepath.Join(dir, fmt.Sprintf("crash-%d-heap.pprof", r.Timestamp.UnixNano()))
	f, err := os.Create(profPath)
	if err != nil {
		return path, err
	}
	defer f.Close()
	// A heap profile may fail if profiling is disabled; the report is
	// still valid without it.
	_ = pprof.WriteHeapProfile(f)
	return path, nil
}

// prune keeps only the newest RetainedMax crash reports in dir.
func prune(dir string) error {
	entries, err := filepath.Glob(filepath.Join(dir, "crash-*.txt"))
	if err != nil {
		return err
	}
	if len(entries) <= RetainedMax {
		return nil
	}
	// Sort by name (timestamps prefix-sort chronologically).
	for i := 1; i < len(entries); i++ {
		for j := i; j > 0 && entries[j] < entries[j-1]; j-- {
			entries[j], entries[j-1] = entries[j-1], entries[j]
		}
	}
	toRemove := len(entries) - RetainedMax
	if toRemove < 0 {
		toRemove = 0
	}
	for _, p := range entries[:toRemove] {
		if err := os.Remove(p); err != nil {
			return err
		}
	}
	return nil
}

// Count returns the number of stored reports in dir.
func Count(dir string) int {
	entries, err := filepath.Glob(filepath.Join(dir, "crash-*.txt"))
	if err != nil {
		return 0
	}
	return len(entries)
}
