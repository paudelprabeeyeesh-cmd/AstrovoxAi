package middleware

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"github.com/astrovox/astrovox/internal/api/logging"
	"github.com/astrovox/astrovox/internal/api/metrics"
	"github.com/astrovox/astrovox/internal/api/tracing"
)

func captureLog(t *testing.T) (*logging.Logger, *bytes.Buffer) {
	t.Helper()
	var buf bytes.Buffer
	l := logging.New("test")
	l.SetOutput(&buf)
	return l, &buf
}

func okHandler() http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})
}

func serve(handler http.Handler) *httptest.ResponseRecorder {
	req := httptest.NewRequest("GET", "/x", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	return rec
}

// --- CORS ------------------------------------------------------------------

func TestCORSEmitsHeadersForAnAllowedOrigin(t *testing.T) {
	h := CORS([]string{"https://app.example.com"})(okHandler())
	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("Origin", "https://app.example.com")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "https://app.example.com" {
		t.Fatalf("allow-origin = %q, want the configured origin", got)
	}
	// Vary is required, or a shared cache can serve one tenant's answer for a
	// different origin.
	if got := rec.Header().Get("Vary"); got != "Origin" {
		t.Fatalf("Vary = %q, want Origin", got)
	}
}

func TestCORSSilentlyIgnoresAnUnlistedOrigin(t *testing.T) {
	h := CORS([]string{"https://app.example.com"})(okHandler())
	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("Origin", "https://evil.example")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if got := rec.Header().Get("Access-Control-Allow-Origin"); got != "" {
		t.Fatalf("allow-origin = %q, want empty for an unlisted origin", got)
	}
}

func TestCORSWithAnEmptyListEmitsNothing(t *testing.T) {
	// The safe default for a non-browser-facing API.
	h := CORS(nil)(okHandler())
	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("Origin", "https://anything.example")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Header().Get("Access-Control-Allow-Origin") != "" {
		t.Fatal("a nil allow-list emitted CORS headers")
	}
}

func TestPreflightIsAnsweredWithoutReachingTheHandler(t *testing.T) {
	reached := false
	h := CORS([]string{"https://app.example.com"})(http.HandlerFunc(
		func(w http.ResponseWriter, r *http.Request) { reached = true },
	))
	req := httptest.NewRequest("OPTIONS", "/x", nil)
	req.Header.Set("Origin", "https://app.example.com")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Fatalf("preflight status = %d, want 204", rec.Code)
	}
	if reached {
		t.Fatal("a preflight request reached the handler")
	}
}

// --- BodyLimit -------------------------------------------------------------

func TestBodyLimitRefusesBeforeReadingTheBody(t *testing.T) {
	h := BodyLimit(10)(okHandler())
	req := httptest.NewRequest("POST", "/x", strings.NewReader(strings.Repeat("a", 4096)))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("status = %d, want 413", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "too large") {
		t.Fatalf("body = %q", rec.Body.String())
	}
}

func TestBodyLimitAdmitsAConformingBody(t *testing.T) {
	h := BodyLimit(4096)(okHandler())
	req := httptest.NewRequest("POST", "/x", strings.NewReader("small"))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
}

// --- Recover ---------------------------------------------------------------

func TestRecoverTurnsAPanicIntoA500Envelope(t *testing.T) {
	log, _ := captureLog(t)
	h := Recover(log)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		panic("nil map write with internal state")
	}))
	rec := serve(h)

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", rec.Code)
	}
	// The panic text must never reach the client.
	if strings.Contains(rec.Body.String(), "nil map write") {
		t.Fatal("the panic value leaked into the response body")
	}
}

func TestRecoverLogsThePanicWithTheRequestID(t *testing.T) {
	log, buf := captureLog(t)
	// Tracing is listed first, so it runs outermost and the id exists before
	// a panic in a later layer can be logged with it.
	h := Chain(panicHandler(), tracing.Middleware, Recover(log))
	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set(tracing.Header, "trace-123")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	out := buf.String()
	if !strings.Contains(out, `"request_id":"trace-123"`) {
		t.Fatalf("the panic was not logged with the request id:\n%s", out)
	}
}

func panicHandler() http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		panic("boom")
	})
}

// --- Log -------------------------------------------------------------------

func TestLogEmitsOneLineWithTheRequestID(t *testing.T) {
	log, buf := captureLog(t)
	h := Chain(okHandler(), tracing.Middleware, Log(log))
	req := httptest.NewRequest("GET", "/things/1", nil)
	req.Header.Set(tracing.Header, "trace-9")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	out := buf.String()
	if strings.Count(out, "\n") != 1 {
		t.Fatalf("%d lines logged, want 1", strings.Count(out, "\n"))
	}
	var entry map[string]interface{}
	if err := json.Unmarshal([]byte(strings.TrimSpace(out)), &entry); err != nil {
		t.Fatalf("log line is not JSON: %v", err)
	}
	if entry["request_id"] != "trace-9" {
		t.Fatalf("request_id = %v", entry["request_id"])
	}
	if entry["path"] != "/things/1" {
		t.Fatalf("path = %v", entry["path"])
	}
}

func TestLogRedactsACookieBearingHeader(t *testing.T) {
	// The logger's redaction must apply to what the middleware logs too, not
	// only to what a caller passes directly.
	log, buf := captureLog(t)
	h := Chain(okHandler(), tracing.Middleware, Log(log))
	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("Cookie", "session=super-secret-value")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if strings.Contains(buf.String(), "super-secret-value") {
		t.Fatal("a cookie value leaked into the log")
	}
}

// --- Metrics ---------------------------------------------------------------

func TestMetricsRecordsTheRequest(t *testing.T) {
	SetTrustProxy(false)
	m := metrics.New()
	m.RegisterPathTemplate("/things/{id}")
	h := Chain(okHandler(), tracing.Middleware, Metrics(m))

	req := httptest.NewRequest("GET", "/things/42", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	// The route label must be the template, not the concrete id.
	got := renderMetrics(t, m)
	if !strings.Contains(got, `http_requests_total{method="GET",route="/things/{id}"} 1`) {
		t.Fatalf("metrics not recorded with a bounded route:\n%s", got)
	}
}

func TestMetricsRecordsAnErrorRate(t *testing.T) {
	SetTrustProxy(false)
	m := metrics.New()
	h := Chain(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}), tracing.Middleware, Metrics(m))

	req := httptest.NewRequest("GET", "/fail", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	got := renderMetrics(t, m)
	if !strings.Contains(got, "http_request_errors_total") ||
		!strings.Contains(got, "} 1") {
		t.Fatalf("an error rate was not recorded:\n%s", got)
	}
}

// --- Chain ordering --------------------------------------------------------

func TestChainAppliesTheFirstLayerOutermost(t *testing.T) {
	var order []string
	record := func(name string) func(http.Handler) http.Handler {
		return func(next http.Handler) http.Handler {
			return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				order = append(order, name)
				next.ServeHTTP(w, r)
			})
		}
	}
	h := Chain(
		http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			order = append(order, "handler")
		}),
		record("outer"), record("inner"),
	)
	serve(h)
	if strings.Join(order, ",") != "outer,inner,handler" {
		t.Fatalf("order = %v, want outer first", order)
	}
}

func TestRecoveryOutsideLoggingKeepsBoth(t *testing.T) {
	// The documented order: recovery outside logging means a panicking
	// request is both logged and answered, rather than one or neither.
	log, buf := captureLog(t)
	h := Chain(panicHandler(), Log(log), Recover(log), tracing.Middleware)
	rec := serve(h)
	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", rec.Code)
	}
	if buf.String() == "" {
		t.Fatal("the panic was not logged")
	}
}

// --- clientIP --------------------------------------------------------------

func TestClientIPIgnoresTheForwardedHeaderByDefault(t *testing.T) {
	// Reading X-Forwarded-For unconditionally lets any client claim any IP
	// and hop rate-limit buckets.
	SetTrustProxy(false)
	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("X-Forwarded-For", "1.2.3.4")
	req.RemoteAddr = "10.0.0.9:1234"
	if got := clientIP(req); got != "10.0.0.9" {
		t.Fatalf("clientIP = %q, want the socket address", got)
	}
}

func TestClientIPHonoursTheForwardedHeaderWhenTrusted(t *testing.T) {
	SetTrustProxy(true)
	defer SetTrustProxy(false)
	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("X-Forwarded-For", "203.0.113.5, 10.0.0.1")
	req.RemoteAddr = "10.0.0.9:1234"
	if got := clientIP(req); got != "203.0.113.5" {
		t.Fatalf("clientIP = %q, want the first forwarded hop", got)
	}
}

// --- Concurrency -----------------------------------------------------------

func TestMiddlewareIsSafeUnderConcurrentLoad(t *testing.T) {
	SetTrustProxy(false)
	log, _ := captureLog(t)
	m := metrics.New()
	h := Chain(okHandler(), tracing.Middleware, Log(log), Metrics(m))

	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			serve(h)
		}()
	}
	wg.Wait()

	got := renderMetrics(t, m)
	if !strings.Contains(got, `http_requests_total{method="GET",route="/x"} 50`) {
		t.Fatalf("50 concurrent requests were not all counted:\n%s", got)
	}
}

// --- helpers ---------------------------------------------------------------

func renderMetrics(t *testing.T, m *metrics.Registry) string {
	t.Helper()
	rec := httptest.NewRecorder()
	m.Handler().ServeHTTP(rec, httptest.NewRequest("GET", "/metrics", nil))
	return rec.Body.String()
}
