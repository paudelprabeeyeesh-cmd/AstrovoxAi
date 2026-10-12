// Package middleware composes the cross-cutting request pipeline in Go:
// tracing, structured logging, metrics, body limits, and CORS.
//
// Order is the whole design. The pipeline runs in the order the layers are
// applied, and each layer's position decides what it can see:
//
//  1. Recovery first, so a panic in any later layer still produces a 500
//     envelope rather than a dropped connection.
//  2. Request id and tracing, so every later layer can log with the same id.
//  3. Body limits, before anything reads the body.
//  4. Logging, which needs the id and wraps the duration metric.
//  5. Metrics, which needs the final status, so it is innermost.
//
// A different order breaks something visible: logging outside recovery loses
// panics, metrics outside body-limits counts requests it should have refused,
// and tracing outside recovery means a panicking request has no trace.
package middleware

import (
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/astrovox/astrovox/internal/api/logging"
	"github.com/astrovox/astrovox/internal/api/metrics"
	"github.com/astrovox/astrovox/internal/api/tracing"
	apperrors "github.com/astrovox/astrovox/internal/errors"
)

// CORS applies an origin allow-list.
//
// An empty list emits no CORS headers at all, which is the safe default for
// an API that is not browser-facing. A '*' is refused at configuration time
// rather than handled here, because pairing it with credentials enabled is a
// known credential-leak misconfiguration.
func CORS(allowed []string) func(http.Handler) http.Handler {
	set := map[string]bool{}
	for _, o := range allowed {
		set[o] = true
	}
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if origin != "" && set[origin] {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				// Vary is required, or a cache can serve one tenant's
				// allow-listed origin to another.
				w.Header().Set("Vary", "Origin")
				w.Header().Set("Access-Control-Allow-Credentials", "true")
			}
			if r.Method == http.MethodOptions {
				w.Header().Set("Access-Control-Allow-Methods",
					"GET, POST, PATCH, PUT, DELETE, OPTIONS")
				w.Header().Set("Access-Control-Allow-Headers",
					"Authorization, Content-Type, X-Request-ID, Idempotency-Key")
				w.Header().Set("Access-Control-Max-Age", "600")
				w.WriteHeader(http.StatusNoContent)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

// BodyLimit rejects a request whose declared length exceeds the limit,
// before the body is read.
func BodyLimit(limit int64) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.ContentLength > limit {
				writeStatus(w, r, http.StatusRequestEntityTooLarge,
					apperrors.New(apperrors.CodeOutOfRange, "request body too large").
						WithField("limit_bytes", limit).
						WithField("size_bytes", r.ContentLength))
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

// Recover converts a panic into a 500 rather than a dropped connection.
func Recover(log *logging.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if rec := recover(); rec != nil {
					// The panic value is logged, never returned: it can carry
					// internal state and a stack trace.
					log.Error("request panicked").
						Field("panic", rec).
						Field("request_id", tracing.FromContext(r.Context())).
						Field("path", r.URL.Path).
						Write()
					writeStatus(w, r, http.StatusInternalServerError,
						apperrors.New(apperrors.CodeInternal, "internal error"))
				}
			}()
			next.ServeHTTP(w, r)
		})
	}
}

// Log emits one line per request with the duration, and attaches the request
// id to the response.
func Log(log *logging.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
			id := tracing.FromContext(r.Context())
			next.ServeHTTP(rec, r.WithContext(tracing.WithID(r.Context(), id)))

			log.Info("handled request").
				Field("request_id", id).
				Field("method", r.Method).
				Field("path", r.URL.Path).
				Field("status", rec.status).
				Field("duration_ms", time.Since(start).Milliseconds()).
				Field("client_ip", clientIP(r)).
				Write()
		})
	}
}

// Metrics records request rate, duration and error rate with a bounded route
// label.
func Metrics(m *metrics.Registry) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
			next.ServeHTTP(rec, r)

			labels := map[string]string{
				"method": r.Method,
				"route":  m.PathLabel(r.URL.Path),
			}
			m.Incr("http_requests_total", labels)
			m.Observe("http_request_duration_seconds", labels, time.Since(start).Seconds())
			if rec.status >= 500 {
				m.Incr("http_request_errors_total", labels)
			}
		})
	}
}

// Chain applies middlewares so the first listed runs outermost, which is the
// order the package comment documents.
func Chain(h http.Handler, layers ...func(http.Handler) http.Handler) http.Handler {
	for i := len(layers) - 1; i >= 0; i-- {
		h = layers[i](h)
	}
	return h
}

// --- helpers ---------------------------------------------------------------

// clientIP resolves the caller. Behind a reverse proxy the proxy's address
// would collapse every user into one bucket, so the forwarded value is read
// only when the deployment says the proxy is trusted.
func clientIP(r *http.Request) string {
	if trusted {
		if fwd := r.Header.Get("X-Forwarded-For"); fwd != "" {
			if idx := strings.Index(fwd, ","); idx > 0 {
				return strings.TrimSpace(fwd[:idx])
			}
			return strings.TrimSpace(fwd)
		}
	}
	if r.RemoteAddr != "" {
		if idx := strings.LastIndex(r.RemoteAddr, ":"); idx > 0 {
			return r.RemoteAddr[:idx]
		}
	}
	return r.RemoteAddr
}

// trusted is set by SetTrustProxy. It is package state because the
// middleware constructors are called before the config exists in some tests;
// it defaults to false, so the unsafe behaviour is opt-in.
var trusted bool

// SetTrustProxy configures whether X-Forwarded-For is honoured.
func SetTrustProxy(v bool) { trusted = v }

// writeStatus renders an error with an explicit status, which the engine's
// code-to-HTTP table alone cannot express (a 413 maps to nothing).
func writeStatus(w http.ResponseWriter, r *http.Request, status int, err error) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set(tracing.Header, tracing.FromContext(r.Context()))
	w.WriteHeader(status)
	env := map[string]interface{}{
		"status":     status,
		"request_id": tracing.FromContext(r.Context()),
		"error": map[string]string{
			"message": err.Error(),
		},
	}
	_ = json.NewEncoder(w).Encode(env)
}

// statusRecorder captures the status without buffering the body.
type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (s *statusRecorder) WriteHeader(code int) {
	if !s.wroteHeader {
		s.status = code
		s.wroteHeader = true
	}
	s.ResponseWriter.WriteHeader(code)
}

func (s *statusRecorder) Write(b []byte) (int, error) {
	if !s.wroteHeader {
		s.wroteHeader = true
	}
	return s.ResponseWriter.Write(b)
}
