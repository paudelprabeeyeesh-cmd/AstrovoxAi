package httpapi

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/astrovox/astrovox/internal/errors"
)

// --- Envelope --------------------------------------------------------------

func do(t *testing.T, r *Router, method, path string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, nil)
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)
	return rec
}

func decodeEnv(t *testing.T, rec *httptest.ResponseRecorder) Envelope {
	t.Helper()
	var env Envelope
	if err := json.Unmarshal(rec.Body.Bytes(), &env); err != nil {
		t.Fatalf("response is not a valid envelope: %v\nbody: %s", err, rec.Body.String())
	}
	return env
}

func TestRespondWritesSuccessEnvelope(t *testing.T) {
	r := NewRouter()
	r.Handle("GET", "/things/{id}", func(c *Context) error {
		if c.Params["id"] != "abc" {
			t.Fatalf("path param not captured: %q", c.Params["id"])
		}
		return Respond(c, http.StatusOK, map[string]string{"name": "thing"})
	})
	rec := do(t, r, "GET", "/things/abc")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	env := decodeEnv(t, rec)
	if env.Error != nil {
		t.Fatalf("success envelope must not carry an error: %+v", env.Error)
	}
	if env.RequestID == "" {
		t.Fatal("success envelope must carry a request id")
	}
	data, ok := env.Data.(map[string]interface{})
	if !ok || data["name"] != "thing" {
		t.Fatalf("data = %#v, want the handler's payload", env.Data)
	}
}

// --- Error codes -----------------------------------------------------------

func TestInvalidArgumentMapsTo400(t *testing.T) {
	r := NewRouter()
	r.Handle("POST", "/x", func(c *Context) error {
		return errors.New(errors.CodeInvalidArgument, "bad input")
	})
	rec := do(t, r, "POST", "/x")
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
	if got := decodeEnv(t, rec).Error.Code; got != "1" {
		t.Logf("code = %q (stable engine code digits)", got)
	}
}

func TestNotFoundMapsTo404(t *testing.T) {
	r := NewRouter()
	r.Handle("GET", "/x", func(c *Context) error {
		return errors.New(errors.CodeNotFound, "missing")
	})
	rec := do(t, r, "GET", "/x")
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
}

func TestPermissionDeniedMapsTo403(t *testing.T) {
	r := NewRouter()
	r.Handle("GET", "/x", func(c *Context) error {
		return errors.New(errors.CodePermissionDenied, "no")
	})
	rec := do(t, r, "GET", "/x")
	// 403 rather than 401: with a single engine code the safer default is
	// not to reveal whether the resource exists.
	if rec.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", rec.Code)
	}
}

func TestRateLimitedCarriesRetryAfter(t *testing.T) {
	r := NewRouter()
	r.Handle("GET", "/x", func(c *Context) error {
		return errors.New(errors.CodeResourceExhausted, "slow down").
			WithField("retry_after", 42)
	})
	rec := do(t, r, "GET", "/x")
	if rec.Code != http.StatusTooManyRequests {
		t.Fatalf("status = %d, want 429", rec.Code)
	}
	if got := rec.Header().Get("Retry-After"); got != "42" {
		t.Fatalf("Retry-After = %q, want 42", got)
	}
	if got := decodeEnv(t, rec).RetryAfter; got != 42 {
		t.Fatalf("envelope retry_after = %d, want 42", got)
	}
}

// --- Internal errors must not leak ----------------------------------------

func TestInternalErrorIsSanitised(t *testing.T) {
	// The message a caller sees must not name the internal failure. A plain
	// error is internal by definition, so its text must never reach the
	// client.
	r := NewRouter()
	r.Handle("GET", "/x", func(c *Context) error {
		return errString("connection to 10.0.0.5:5432 refused")
	})
	rec := do(t, r, "GET", "/x")
	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", rec.Code)
	}
	env := decodeEnv(t, rec)
	if env.Error == nil || env.Error.Message != "Internal error" {
		t.Fatalf("message = %q, want the generic one", env.Error.Message)
	}
	if strings.Contains(rec.Body.String(), "10.0.0.5") {
		t.Fatal("internal detail leaked into the response body")
	}
}

func TestInternalEngineErrorIsSanitised(t *testing.T) {
	r := NewRouter()
	r.Handle("GET", "/x", func(c *Context) error {
		return errors.New(errors.CodeInternal, "sql: connection string had \"password\"")
	})
	rec := do(t, r, "GET", "/x")
	if strings.Contains(rec.Body.String(), "password") {
		t.Fatal("engine error text leaked into the response body")
	}
}

// --- Request id ------------------------------------------------------------

func TestCallerRequestIDIsHonouredAndSanitised(t *testing.T) {
	r := NewRouter()
	r.Handle("GET", "/x", func(c *Context) error {
		return Respond(c, http.StatusOK, nil)
	})

	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("X-Request-ID", "trace-123")
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)
	if got := rec.Header().Get("X-Request-ID"); got != "trace-123" {
		t.Fatalf("X-Request-ID = %q, want trace-123", got)
	}

	// A header with control characters must not reach a log line intact.
	req = httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("X-Request-ID", "bad\"id\ninjected")
	rec = httptest.NewRecorder()
	r.ServeHTTP(rec, req)
	got := rec.Header().Get("X-Request-ID")
	if strings.ContainsAny(got, "\"\n") {
		t.Fatalf("request id was not sanitised: %q", got)
	}
	if got == "" {
		t.Fatal("a missing id must be replaced, not left empty")
	}
}

func TestMissingRequestIDIsGenerated(t *testing.T) {
	r := NewRouter()
	r.Handle("GET", "/x", func(c *Context) error { return Respond(c, http.StatusOK, nil) })
	rec := do(t, r, "GET", "/x")
	if rec.Header().Get("X-Request-ID") == "" {
		t.Fatal("no request id was generated")
	}
}

// --- Binding ---------------------------------------------------------------

func TestBindRejectsTrailingData(t *testing.T) {
	r := NewRouter()
	r.Handle("POST", "/x", func(c *Context) error {
		var dst struct {
			A int `json:"a"`
		}
		if err := c.Bind(&dst); err != nil {
			return err
		}
		return Respond(c, http.StatusOK, dst)
	})
	// Two JSON objects: the decoder would silently read only the first.
	rec := doBody(t, r, "POST", "/x", `{"a":1}{"b":2}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400 for a body with trailing data", rec.Code)
	}
}

func TestBindRejectsOversizedBody(t *testing.T) {
	r := NewRouter()
	r.Handle("POST", "/x", func(c *Context) error {
		var dst struct {
			Blob string `json:"blob"`
		}
		if err := c.Bind(&dst); err != nil {
			return err
		}
		return Respond(c, http.StatusOK, dst)
	})
	// maxBodyBytes is the byte cap, so a body of that many literal
	// characters plus the JSON wrapper necessarily exceeds it. An earlier
	// version divided by four and produced a body half the cap.
	body := `{"blob":"` + strings.Repeat("x", maxBodyBytes) + `"}`
	rec := doBody(t, r, "POST", "/x", body)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400 for an oversized body (sent %d bytes)", rec.Code, len(body))
	}
}

func TestBodyLimitMiddlewareRejectsDeclaredSize(t *testing.T) {
	r := NewRouter()
	r.Use(BodyLimitMiddleware(16))
	r.Handle("POST", "/x", func(c *Context) error {
		return Respond(c, http.StatusOK, "inside")
	})
	req := httptest.NewRequest("POST", "/x", strings.NewReader(strings.Repeat("y", 4096)))
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
}

// --- Panic recovery --------------------------------------------------------

func TestRecoverMiddlewareTurnsAPanicInto500(t *testing.T) {
	r := NewRouter()
	r.Use(RecoverMiddleware)
	r.Handle("GET", "/boom", func(c *Context) error {
		panic("nil map write")
	})
	rec := do(t, r, "GET", "/boom")
	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", rec.Code)
	}
	if strings.Contains(rec.Body.String(), "nil map write") {
		t.Fatal("panic text leaked to the client")
	}
}

// --- Middleware ordering ---------------------------------------------------

func TestMiddlewareRunsInRegistrationOrder(t *testing.T) {
	var order []string
	r := NewRouter()
	r.Use(func(next Handler) Handler {
		return func(c *Context) error {
			order = append(order, "outer")
			return next(c)
		}
	})
	r.Use(func(next Handler) Handler {
		return func(c *Context) error {
			order = append(order, "inner")
			return next(c)
		}
	})
	r.Handle("GET", "/x", func(c *Context) error {
		order = append(order, "handler")
		return Respond(c, http.StatusOK, nil)
	})
	do(t, r, "GET", "/x")
	want := []string{"outer", "inner", "handler"}
	if strings.Join(order, ",") != strings.Join(want, ",") {
		t.Fatalf("order = %v, want %v", order, want)
	}
}

// --- Route table -----------------------------------------------------------

func TestPatternsRecordsRegisteredRoutes(t *testing.T) {
	r := NewRouter()
	r.Handle("GET", "/a", func(c *Context) error { return nil })
	r.Handle("POST", "/b/{id}", func(c *Context) error { return nil })
	got := strings.Join(r.Patterns(), " ")
	for _, want := range []string{"GET /a", "POST /b/{id}"} {
		if !strings.Contains(got, want) {
			t.Fatalf("patterns %q missing %q", got, want)
		}
	}
}

func TestMethodMismatchIs405(t *testing.T) {
	r := NewRouter()
	r.Handle("POST", "/x", func(c *Context) error { return Respond(c, http.StatusOK, nil) })
	rec := do(t, r, "GET", "/x")
	if rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("status = %d, want 405", rec.Code)
	}
}

// --- Query helpers ---------------------------------------------------------

func TestQueryIntFallsBack(t *testing.T) {
	if got := (&Context{Request: httptest.NewRequest("GET", "/x?n=7", nil)}).QueryInt("n", 3); got != 7 {
		t.Fatalf("QueryInt(n) = %d, want 7", got)
	}
	if got := (&Context{Request: httptest.NewRequest("GET", "/x?n=abc", nil)}).QueryInt("n", 3); got != 3 {
		t.Fatalf("QueryInt(bad) = %d, want the default 3", got)
	}
	if got := (&Context{Request: httptest.NewRequest("GET", "/x", nil)}).QueryInt("n", 3); got != 3 {
		t.Fatalf("QueryInt(missing) = %d, want the default 3", got)
	}
}

func TestBearerIsCaseInsensitive(t *testing.T) {
	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("Authorization", "bearer tok")
	if got := (&Context{Request: req}).Bearer(); got != "tok" {
		t.Fatalf("Bearer() = %q, want tok", got)
	}
	req = httptest.NewRequest("GET", "/x", nil)
	req.Header.Set("Authorization", "Basic abc")
	if got := (&Context{Request: req}).Bearer(); got != "" {
		t.Fatalf("Bearer() = %q, want empty for a non-bearer scheme", got)
	}
}

// --- helpers ---------------------------------------------------------------

// errString is a plain error, which the router must treat as internal.
type errString string

func (e errString) Error() string { return string(e) }

func doBody(t *testing.T, r *Router, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)
	return rec
}
