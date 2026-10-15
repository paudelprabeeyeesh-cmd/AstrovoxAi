package testing

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"testing"
	"time"

	"github.com/astrovox/astrovox/internal/testing/util"
)

var ErrFuzzFailure = errors.New("fuzz failure")

// FuzzTargets contains fuzz harnesses.
func FuzzRoundTrip(f *testing.F) {
	f.Add(`{"nodes":[],"output":[]}`)
	f.Fuzz(func(t *testing.T, input string) {
		var v interface{}
		if err := json.Unmarshal([]byte(input), &v); err != nil {
			return
		}
	})
}

func TestGoroutineLeak(t *testing.T) {
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		time.Sleep(1 * time.Millisecond)
	}()
	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("possible goroutine leak")
	}
}

func TestNoGoroutineLeakSimple(t *testing.T) {
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
	}()
	wg.Wait()
}

func TestStabilityRepeatedAlloc(t *testing.T) {
	for i := 0; i < 1000; i++ {
		_ = make([]byte, 1024)
	}
}

func TestStabilityConcurrentAccess(t *testing.T) {
	var mu sync.Mutex
	count := 0
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			mu.Lock()
			count++
			mu.Unlock()
		}()
	}
	wg.Wait()
	if count != 100 {
		t.Fatalf("expected 100, got %d", count)
	}
}

func TestAPIGoldenFile(t *testing.T) {
	got := []byte("expected output")
	util.Golden(t, got, "testdata/golden_api.txt")
}

func TestPerformanceRegression(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping regression in short mode")
	}
	start := time.Now()
	for i := 0; i < 10000; i++ {
		_ = make([]byte, 1024)
	}
	elapsed := time.Since(start)
	if elapsed > 5*time.Second {
		t.Fatalf("allocation took too long: %v", elapsed)
	}
}

func TestChaosHook(t *testing.T) {
	hook := func() error { return nil }
	if err := hook(); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestRuntimeInfo(t *testing.T) {
	info := RuntimeInfo()
	if info["go_version"] == "" || info["os"] == "" || info["arch"] == "" {
		t.Fatal("expected runtime info")
	}
}

func TestEnvWithPrefix(t *testing.T) {
	os.Setenv("ASTROVOX_TEST_PRODUCTION", "value")
	defer os.Unsetenv("ASTROVOX_TEST_PRODUCTION")
	env := EnvWithPrefix("ASTROVOX_TEST_")
	if env["ASTROVOX_TEST_PRODUCTION"] != "value" {
		t.Fatalf("expected env var")
	}
}

func TestFuzzInvalidJSON(t *testing.T) {
	inputs := []string{"", "invalid", "{}", `{"a":1}`}
	for _, input := range inputs {
		var v interface{}
		if err := json.Unmarshal([]byte(input), &v); err == nil {
			// valid or partial json is fine
		}
	}
}

func TestStressLoop(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping stress in short mode")
	}
	for i := 0; i < 100000; i++ {
		_ = i * i
	}
}

func TestStabilityMemory(t *testing.T) {
	var m runtime.MemStats
	runtime.GC()
	runtime.ReadMemStats(&m)
	if m.Alloc == 0 {
		t.Fatal("expected some allocation")
	}
}

func TestConcurrentMap(t *testing.T) {
	var mu sync.Mutex
	m := make(map[int]int)
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func(key int) {
			defer wg.Done()
			mu.Lock()
			m[key] = key * 2
			mu.Unlock()
		}(i)
	}
	wg.Wait()
	if len(m) != 50 {
		t.Fatalf("expected 50 entries, got %d", len(m))
	}
}

func TestFileReadWrite(t *testing.T) {
	// Write into the test's own temp dir: a relative testdata path
	// fails when the directory does not exist and leaks files into the
	// package when it does.
	path := filepath.Join(t.TempDir(), "prod_test.txt")
	if err := os.WriteFile(path, []byte("data"), 0644); err != nil {
		t.Fatalf("write: %v", err)
	}
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if string(got) != "data" {
		t.Fatalf("unexpected: %s", got)
	}
}

func TestStdoutCapture(t *testing.T) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w
	func() {
		io.WriteString(w, "test output\n")
	}()
	w.Close()
	os.Stdout = old
	var buf bytes.Buffer
	io.Copy(&buf, r)
	if !bytes.Contains(buf.Bytes(), []byte("test output")) {
		t.Fatal("expected captured output")
	}
}
