package logging

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"sync"
	"testing"
)

func capture(t *testing.T, fn func(l *Logger)) string {
	t.Helper()
	var buf bytes.Buffer
	l := New("test")
	l.SetOutput(&buf)
	fn(l)
	return buf.String()
}

func decode(t *testing.T, line string) map[string]interface{} {
	t.Helper()
	var out map[string]interface{}
	if err := json.Unmarshal([]byte(line), &out); err != nil {
		t.Fatalf("log line is not JSON: %v\n%s", err, line)
	}
	return out
}

func TestEveryLineIsJSONWithTheStandardKeys(t *testing.T) {
	out := capture(t, func(l *Logger) { l.Info("hello").Write() })
	fields := decode(t, strings.TrimSpace(out))
	for _, key := range []string{"service", "level", "message", "timestamp"} {
		if _, ok := fields[key]; !ok {
			t.Fatalf("missing %q in %s", key, out)
		}
	}
	if fields["message"] != "hello" {
		t.Fatalf("message = %v", fields["message"])
	}
	if fields["level"] != "info" {
		t.Fatalf("level = %v", fields["level"])
	}
}

func TestRedactedKeysNeverAppearInALine(t *testing.T) {
	// The central property: a caller cannot pass a credential through the
	// logger, because the key set is closed and the redaction is here rather
	// than at every call site.
	out := capture(t, func(l *Logger) {
		l.Info("signin").
			Field("token", "sk-live-super-secret").
			Field("authorization", "Bearer abc123").
			Field("password", "hunter2").
			Field("api_key", "AKIA1234567890").
			Field("email", "user@example.com").
			Write()
	})
	for _, secret := range []string{"sk-live-super-secret", "abc123", "hunter2", "AKIA1234567890", "user@example.com"} {
		if strings.Contains(out, secret) {
			t.Fatalf("secret %q leaked into the log line", secret)
		}
	}
	fields := decode(t, strings.TrimSpace(out))
	if fields["token"] != redactedPlaceholder {
		t.Fatalf("token = %v, want the placeholder", fields["token"])
	}
}

func TestRedactionIsCaseInsensitiveOnKeys(t *testing.T) {
	out := capture(t, func(l *Logger) {
		l.Info("x").Field("Access-Token", "secret-value").Write()
	})
	if strings.Contains(out, "secret-value") {
		t.Fatalf("a differently-cased key leaked: %s", out)
	}
}

func TestNestedObjectsAreRedacted(t *testing.T) {
	// A redaction that only covers the top level is a redaction with a hole
	// in it, and the hole is where the secrets actually live.
	out := capture(t, func(l *Logger) {
		l.Info("request").
			Field("headers", map[string]interface{}{
				"Authorization": "Bearer nested-secret",
				"X-Trace":       "keep-me",
			}).
			Write()
	})
	if strings.Contains(out, "nested-secret") {
		t.Fatalf("a nested secret leaked: %s", out)
	}
	if !strings.Contains(out, "keep-me") {
		t.Fatalf("a benign nested field was redacted: %s", out)
	}
}

func TestListsOfObjectsAreRedacted(t *testing.T) {
	out := capture(t, func(l *Logger) {
		l.Info("batch").
			Field("items", []interface{}{
				map[string]interface{}{"token": "t1"},
				map[string]interface{}{"token": "t2"},
			}).
			Write()
	})
	if strings.Contains(out, "t1") || strings.Contains(out, "t2") {
		t.Fatalf("secrets inside a list leaked: %s", out)
	}
}

func TestLevelThresholdIsHonoured(t *testing.T) {
	var buf bytes.Buffer
	l := New("test")
	l.SetOutput(&buf)
	l.SetLevel(LevelWarn)

	l.Info("dropped").Write()
	l.Debug("dropped").Write()
	l.Warn("kept").Write()
	l.Error("kept").Write()

	out := buf.String()
	if strings.Contains(out, "dropped") {
		t.Fatalf("a below-threshold entry was written:\n%s", out)
	}
	if strings.Count(out, "\n") != 2 {
		t.Fatalf("%d lines written, want 2", strings.Count(out, "\n"))
	}
}

func TestParseLevelCoversTheNames(t *testing.T) {
	cases := map[string]Level{
		"debug": LevelDebug, "DEBUG": LevelDebug,
		"info": LevelInfo, "": LevelInfo, "bogus": LevelInfo,
		"warn": LevelWarn, "warning": LevelWarn,
		"error": LevelError, "fatal": LevelError,
	}
	for name, want := range cases {
		if got := ParseLevel(name); got != want {
			t.Errorf("ParseLevel(%q) = %v, want %v", name, got, want)
		}
	}
}

func TestWithCarriesFieldsOntoEveryLine(t *testing.T) {
	out := capture(t, func(l *Logger) {
		derived := l.With(map[string]string{"request_id": "abc"})
		derived.Info("one").Write()
		derived.Info("two").Write()
	})
	if strings.Count(out, `"request_id":"abc"`) != 2 {
		t.Fatalf("the derived field is not on every line:\n%s", out)
	}
}

func TestErrRecordsTheErrorMessage(t *testing.T) {
	out := capture(t, func(l *Logger) {
		l.Error("failed").Err(context.DeadlineExceeded).Write()
	})
	fields := decode(t, strings.TrimSpace(out))
	if fields["error"] != "context deadline exceeded" {
		t.Fatalf("error = %v", fields["error"])
	}
}

func TestErrWithANilErrorIsANoop(t *testing.T) {
	out := capture(t, func(l *Logger) {
		l.Error("x").Err(nil).Write()
	})
	// Match the field, not the substring: "error" also occurs inside
	// "level":"error", so a substring check would pass on the level field.
	fields := decode(t, strings.TrimSpace(out))
	if _, present := fields["error"]; present {
		t.Fatalf("a nil error produced an error field: %s", out)
	}
}

func TestContextLoggerRoundTrips(t *testing.T) {
	l := New("svc")
	ctx := WithLogger(context.Background(), l.With(map[string]string{"k": "v"}))
	got := FromContext(ctx, New("fallback"))
	if got.service["k"] != "v" {
		t.Fatal("the derived logger was not retrieved from the context")
	}
}

func TestContextLoggerFallsBackRatherThanPanicking(t *testing.T) {
	got := FromContext(context.Background(), New("fallback"))
	if got == nil {
		t.Fatal("no logger returned for a bare context")
	}
	if got.service["service"] != "fallback" {
		t.Fatalf("service = %v, want the fallback", got.service["service"])
	}
}

func TestConcurrentWritesProduceIntactLines(t *testing.T) {
	// The shared buffer under a mutex must not interleave half a line.
	var buf bytes.Buffer
	l := New("test")
	l.SetOutput(&buf)
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			l.Info("msg").Field("n", n).Write()
		}(i)
	}
	wg.Wait()
	lines := strings.Split(strings.TrimSpace(buf.String()), "\n")
	if len(lines) != 50 {
		t.Fatalf("%d lines, want 50: writes interleaved", len(lines))
	}
	for _, line := range lines {
		decode(t, line)
	}
}
