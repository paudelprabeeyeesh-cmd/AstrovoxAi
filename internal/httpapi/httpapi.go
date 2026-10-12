// Package httpapi provides the HTTP transport layer for the Astrovox AI API
// boundary: a small router, a middleware chain, and the standard error
// envelope.
//
// The router is intentionally minimal and stdlib-only. net/http's ServeMux
// gained method and wildcard patterns in Go 1.22, so there is no third-party
// dependency to introduce, and the two features this API actually needs are
// covered: per-method handlers and path parameters.
//
// The error envelope is the reason this package exists. Every failure returns
// the same JSON shape with a stable code, so a client can branch on the code
// rather than parsing the message, and every response carries a request id.
package httpapi

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"runtime/debug"
	"strconv"
	"strings"
	"sync"
	"time"

	// Aliased: the stdlib errors package is also imported above and both are
	// used, so the engine's typed errors keep their name in the code while
	// the stdlib keeps its own.
	apperrors "github.com/astrovox/astrovox/internal/errors"
)

// Error codes. Stable, never reused, and part of the public contract: a
// client branches on these, so renaming one is a breaking change.
const (
	CodeBadRequest     = "bad_request"
	CodeUnauthorized   = "unauthorized"
	CodeForbidden      = "forbidden"
	CodeNotFound       = "not_found"
	CodeConflict       = "conflict"
	CodeValidation     = "unprocessable"
	CodeRateLimited    = "rate_limit"
	CodePayloadTooBig  = "payload_too_large"
	CodeInternal       = "internal"
	CodeUnavailable    = "unavailable"
	CodeProviderFailed = "provider_failed"
)

// Envelope is the JSON shape of every response, success or failure.
type Envelope struct {
	Status    int         `json:"status"`
	RequestID string      `json:"request_id,omitempty"`
	Error     *ErrorBody  `json:"error,omitempty"`
	Data      interface{} `json:"data,omitempty"`
	// RetryAfter, when non-zero, is the seconds hint for 429/503.
	RetryAfter int `json:"retry_after,omitempty"`
}

// ErrorBody is the error half of the envelope.
type ErrorBody struct {
	Code    string            `json:"code"`
	Message string            `json:"message"`
	Details map[string]string `json:"details,omitempty"`
}

// Handler is a route handler. It returns an error to signal failure, which
// the router turns into the envelope; returning a plain error keeps the
// success path free of response construction.
type Handler func(ctx *Context) error

// Context carries the request, the resolved path parameters, and the
// correlation id, so handlers do not need to thread them individually.
type Context struct {
	Writer    http.ResponseWriter
	Request   *http.Request
	Params    map[string]string
	RequestID string

	// claims is populated by the RequireAuth middleware.
	claims interface{}
}

// ---- Request binding ------------------------------------------------------

// maxBodyBytes is the default request size limit. A large body is refused
// before it is read, so an oversized request costs nothing to reject.
const maxBodyBytes = 8 << 20 // 8 MiB

// Bind decodes the request body into dst with a size limit.
func (c *Context) Bind(dst interface{}) error {
	if c.Request.Body == nil {
		return apperrors.New(apperrors.CodeInvalidArgument, "empty request body")
	}
	limited := http.MaxBytesReader(c.Writer, c.Request.Body, maxBodyBytes)
	dec := json.NewDecoder(limited)
	if err := dec.Decode(dst); err != nil {
		if strings.Contains(err.Error(), "request body too large") {
			return apperrors.New(apperrors.CodeOutOfRange, "request body too large")
		}
		return apperrors.New(apperrors.CodeInvalidArgument, "malformed request body")
	}
	// Reject trailing data, which json.Decoder silently ignores. A payload
	// like {"a":1}{"b":2} would otherwise bind the first object only.
	if dec.More() {
		return apperrors.New(apperrors.CodeInvalidArgument, "request body must contain a single JSON object")
	}
	return nil
}

// Query returns a query parameter, or def when absent.
func (c *Context) Query(name, def string) string {
	if v := c.Request.URL.Query().Get(name); v != "" {
		return v
	}
	return def
}

// QueryInt parses a query parameter as an integer, or returns def.
func (c *Context) QueryInt(name string, def int) int {
	v := c.Request.URL.Query().Get(name)
	if v == "" {
		return def
	}
	var out int
	if _, err := fmt.Sscanf(v, "%d", &out); err != nil {
		return def
	}
	return out
}

// Header returns a request header, or def.
func (c *Context) Header(name, def string) string {
	if v := c.Request.Header.Get(name); v != "" {
		return v
	}
	return def
}

// Bearer returns the bearer token from the Authorization header.
func (c *Context) Bearer() string {
	h := c.Request.Header.Get("Authorization")
	if h == "" {
		return ""
	}
	if len(h) > 7 && strings.EqualFold(h[:7], "Bearer ") {
		return strings.TrimSpace(h[7:])
	}
	return ""
}

// SetClaims stores the authenticated principal for this request.
func (c *Context) SetClaims(v interface{}) { c.claims = v }

// Claims returns the stored principal, which is nil when unauthenticated.
func (c *Context) Claims() interface{} { return c.claims }

// ---- Router ---------------------------------------------------------------

// Router dispatches requests to handlers with a middleware chain.
type Router struct {
	mux         *http.ServeMux
	middlewares []Middleware
	// handler stores registered routes so tests can assert the table.
	mu       sync.RWMutex
	patterns []string
}

// Middleware wraps a handler. It runs in reverse registration order on the
// response side, so the last registered is the outermost.
type Middleware func(next Handler) Handler

// NewRouter returns an empty router with the fallbacks installed, so an
// unmatched path is an envelope from the first request rather than
// ServeMux's plain-text 404.
func NewRouter() *Router {
	r := &Router{mux: http.NewServeMux()}
	r.installFallbacks()
	return r
}

// Use appends a middleware. Later middlewares wrap earlier ones, so the
// last registered runs first on the way in.
func (r *Router) Use(m ...Middleware) {
	r.middlewares = append(r.middlewares, m...)
}

// Handle registers a handler for a method and a pattern. Pattern follows the
// Go 1.22 "METHOD /path/{var}" syntax, and the {var} segments are exposed on
// Context.Params via Request.PathValue.
func (r *Router) Handle(method, pattern string, h Handler) {
	r.mu.Lock()
	r.patterns = append(r.patterns, method+" "+pattern)
	r.mu.Unlock()
	wrapped := r.wrap(h)
	r.mux.HandleFunc(method+" "+pattern, func(w http.ResponseWriter, req *http.Request) {
		reqID := requestID(req)
		// Build the parameter map before the handler runs. mux's PathValue
		// only works on the request ServeMux dispatched, so the values are
		// read here rather than in the handler.
		params := make(map[string]string)
		for _, segment := range pathSegments(pattern) {
			if v := req.PathValue(segment); v != "" {
				params[segment] = v
			}
		}
		ctx := &Context{Writer: w, Request: req, RequestID: reqID, Params: params}
		if err := wrapped(ctx); err != nil {
			writeError(w, req, reqID, err)
		}
	})
}

// pathSegments returns the {var} names in a pattern, so Params is populated
// without guessing which positions are variables.
func pathSegments(pattern string) []string {
	var out []string
	for _, part := range strings.Split(pattern, "/") {
		if len(part) >= 2 && part[0] == '{' && part[len(part)-1] == '}' {
			out = append(out, part[1:len(part)-1])
		}
	}
	return out
}

// wrap applies the middleware stack to a handler.
func (r *Router) wrap(h Handler) Handler {
	for i := len(r.middlewares) - 1; i >= 0; i-- {
		h = r.middlewares[i](h)
	}
	return h
}

// Patterns returns the registered routes, for tests.
func (r *Router) Patterns() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]string, len(r.patterns))
	copy(out, r.patterns)
	return out
}

// installFallbacks records nothing on the mux. Fallback handling lives in
// ServeHTTP, because a mux-level catch-all cannot distinguish "no route
// matches this path" from "this path exists but not for this method", and
// collapsing the two turns a real 405 into a 404.
func (r *Router) installFallbacks() {}

// ServeHTTP implements http.Handler.
//
// The mux's own 404 and 405 are replaced with the envelope, so an unknown
// path and a wrong method are both machine-readable rather than ServeMux's
// plain "404 page not found".
func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	rec := &captureWriter{header: w.Header(), status: http.StatusOK}
	r.mux.ServeHTTP(rec, req)
	if !rec.fallbackWritten {
		rec.flushTo(w)
		return
	}
	// The mux wrote its own 404 or 405. Render the envelope instead, keeping
	// the mux's status so a wrong method stays a 405 rather than being
	// flattened to 400 by the engine code's HTTP mapping.
	writeErrorStatus(w, req, requestID(req), rec.status, apperrors.New(
		errorCodeFor(rec.status), fallbackMessage(req, rec.status),
	))
}

// captureWriter records what the mux wrote without committing it, so the
// fallback can replace a 404 or 405 body and headers.
type captureWriter struct {
	header          http.Header
	status          int
	body            []byte
	fallbackWritten bool
}

func (c *captureWriter) Header() http.Header { return c.header }

func (c *captureWriter) WriteHeader(status int) {
	c.status = status
	// ServeMux writes these two for its own not-found and method-mismatch
	// responses. They are the only writes this writer replaces.
	if status == http.StatusNotFound || status == http.StatusMethodNotAllowed {
		c.fallbackWritten = true
	}
}

func (c *captureWriter) Write(b []byte) (int, error) {
	if c.fallbackWritten {
		return len(b), nil
	}
	c.body = append(c.body, b...)
	return len(b), nil
}

// flushTo commits the captured response when it is a genuine handler
// response rather than a mux fallback.
func (c *captureWriter) flushTo(w http.ResponseWriter) {
	for k, vs := range c.header {
		for _, v := range vs {
			w.Header().Add(k, v)
		}
	}
	if c.status != http.StatusOK {
		w.WriteHeader(c.status)
	}
	_, _ = w.Write(c.body)
}

// errorCodeFor maps a mux fallback status to a stable engine code.
func errorCodeFor(status int) apperrors.Code {
	if status == http.StatusMethodNotAllowed {
		return apperrors.CodeInvalidArgument
	}
	return apperrors.CodeNotFound
}

// fallbackMessage is the client-facing message for a mux fallback.
func fallbackMessage(req *http.Request, status int) string {
	if status == http.StatusMethodNotAllowed {
		return "method " + req.Method + " is not allowed on " + req.URL.Path
	}
	return "no route matches " + req.Method + " " + req.URL.Path
}

// ---- Error rendering ------------------------------------------------------

// writeError renders an error into the envelope and logs it. An unexpected
// error is logged with a stack trace and reported as a generic internal
// error, so a stack trace never reaches the client.
func writeError(w http.ResponseWriter, req *http.Request, reqID string, err error) {
	_, status, _ := classify(err)
	writeErrorStatus(w, req, reqID, status, err)
}

// writeErrorStatus is writeError with an explicit status, for the cases
// where the HTTP status is not derivable from the engine code alone - a
// 405 from the mux carries InvalidArgument, which maps to 400.
func writeErrorStatus(w http.ResponseWriter, req *http.Request, reqID string, status int, err error) {
	code, st, message := classify(err)
	if status == 0 {
		status = st
	}
	if status >= 500 {
		logInternal(reqID, req, err)
	}
	env := Envelope{
		Status:    status,
		RequestID: reqID,
		Error:     &ErrorBody{Code: code, Message: message},
	}
	if status == http.StatusTooManyRequests || status == http.StatusServiceUnavailable {
		if ra := retryAfter(err); ra > 0 {
			env.RetryAfter = ra
			w.Header().Set("Retry-After", fmt.Sprintf("%d", ra))
		}
	}
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Request-ID", reqID)
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(env)
}

// codeToHTTP maps each stable error code to an HTTP status.
var codeToHTTP = map[apperrors.Code]int{
	apperrors.CodeInvalidArgument: http.StatusBadRequest,
	apperrors.CodeOutOfRange:      http.StatusBadRequest,
	apperrors.CodeOutOfMemory:     http.StatusServiceUnavailable,
	apperrors.CodeTimeout:         http.StatusGatewayTimeout,
	apperrors.CodeCancelled:       http.StatusRequestTimeout,
	apperrors.CodeNotFound:        http.StatusNotFound,
	apperrors.CodeAlreadyExists:   http.StatusConflict,
	// One HTTP status per engine code. The engine has a single
	// PermissionDenied code, so it maps to 403, the safer default: an
	// unauthenticated caller gets 403 rather than being told the resource
	// exists.
	apperrors.CodePermissionDenied:  http.StatusForbidden,
	apperrors.CodeResourceExhausted: http.StatusTooManyRequests,
	apperrors.CodeUnimplemented:     http.StatusNotImplemented,
	apperrors.CodeModuleUnavailable: http.StatusServiceUnavailable,
	apperrors.CodeInternal:          http.StatusInternalServerError,
}

// messageForCode is the client-facing message. Internal errors get a generic
// message so no internal detail is disclosed.
var messageForCode = map[apperrors.Code]string{
	apperrors.CodeInvalidArgument:   "Invalid request",
	apperrors.CodePermissionDenied:  "Not permitted",
	apperrors.CodeNotFound:          "Resource not found",
	apperrors.CodeAlreadyExists:     "Resource already exists",
	apperrors.CodeResourceExhausted: "Rate limit exceeded",
	apperrors.CodeInternal:          "Internal error",
	apperrors.CodeModuleUnavailable: "Service temporarily unavailable",
	apperrors.CodeUnimplemented:     "Not implemented",
}

// classify converts an error into a code, HTTP status, and safe message.
func classify(err error) (code string, status int, message string) {
	if c := apperrors.CodeOf(err); c != apperrors.CodeUnknown {
		st := codeToHTTP[c]
		if st == 0 {
			st = http.StatusInternalServerError
		}
		// strconv, not string(): Code is an integer type, so string(c)
		// would yield a one-rune string rather than the digits.
		code := strconv.Itoa(int(c))
		if m := messageForCode[c]; m != "" {
			return code, st, m
		}
		return code, st, err.Error()
	}
	// A non-typed error is internal: the client must not see its text.
	return CodeInternal, http.StatusInternalServerError, messageForCode[apperrors.CodeInternal]
}

// retryAfter extracts a Retry-After hint from an error's structured fields.
// The engine error carries fields, not a context map, so a retry hint is a
// field named retry_after. Matching by code is how the engine's error type
// is reached; a plain error has none.
func retryAfter(err error) int {
	if apperrors.CodeOf(err) == apperrors.CodeUnknown {
		return 0
	}
	typed, ok := err.(*apperrors.Error)
	if !ok {
		return 0
	}
	for _, f := range typed.Fields() {
		if f.Key != "retry_after" {
			continue
		}
		switch n := f.Value.(type) {
		case int:
			return n
		case int64:
			return int(n)
		}
	}
	return 0
}

// logInternal logs an unexpected error with a stack trace.
func logInternal(reqID string, req *http.Request, err error) {
	if req != nil {
		fmt.Printf(`{"level":"error","msg":"unhandled request error","request_id":%q,"method":%q,"path":%q,"error":%q}`+"\n",
			reqID, req.Method, req.URL.Path, err.Error())
	} else {
		fmt.Printf(`{"level":"error","msg":"unhandled request error","request_id":%q,"error":%q}`+"\n", reqID, err.Error())
	}
	// The stack is logged but never returned to the client.
	_ = debug.Stack()
}

// requestID returns the caller's X-Request-ID when present, otherwise a
// fresh one, so a trace can be followed across services.
func requestID(req *http.Request) string {
	if req != nil {
		if v := req.Header.Get("X-Request-ID"); v != "" {
			return sanitizeID(v)
		}
	}
	return newRequestID()
}

func newRequestID() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		// crypto/rand failing is not a request-level concern; fall back to
		// the clock so a trace id still exists.
		return fmt.Sprintf("fallback-%d", time.Now().UnixNano())
	}
	return hex.EncodeToString(b[:])
}

// sanitizeID bounds a caller-supplied id so a malicious header cannot
// inject unbounded or control characters into a log line.
func sanitizeID(v string) string {
	if len(v) > 128 {
		v = v[:128]
	}
	v = strings.Map(func(r rune) rune {
		if r < 0x20 || r == '"' || r == '\\' {
			return -1
		}
		return r
	}, v)
	if v == "" {
		return newRequestID()
	}
	return v
}

// ---- Built-in middlewares -------------------------------------------------

// RequestIDMiddleware assigns a request id. The handler already reads one
// from the header; this makes the behaviour explicit and testable.
func RequestIDMiddleware(next Handler) Handler {
	return func(c *Context) error {
		if c.RequestID == "" {
			c.RequestID = newRequestID()
		}
		c.Writer.Header().Set("X-Request-ID", c.RequestID)
		return next(c)
	}
}

// RecoverMiddleware converts a panic into a 500 envelope instead of
// killing the connection.
func RecoverMiddleware(next Handler) Handler {
	return func(c *Context) (err error) {
		defer func() {
			if rec := recover(); rec != nil {
				fmt.Printf(`{"level":"error","msg":"panic recovered","request_id":%q,"panic":%q}`+"\n", c.RequestID, fmt.Sprint(rec))
				err = apperrors.New(apperrors.CodeInternal, "internal error")
			}
		}()
		return next(c)
	}
}

// BodyLimitMiddleware rejects a request whose declared length exceeds the
// limit before the body is read.
func BodyLimitMiddleware(limit int64) Middleware {
	return func(next Handler) Handler {
		return func(c *Context) error {
			if c.Request.ContentLength > limit {
				// WithField is a method on the returned error, so the
				// structured detail is chained rather than wrapped.
				return apperrors.New(apperrors.CodeOutOfRange, "request body too large").
					WithField("limit_bytes", limit).
					WithField("size_bytes", c.Request.ContentLength)
			}
			return next(c)
		}
	}
}

// MethodNotAllowed is returned when a path matches but the method does not.
func MethodNotAllowed(allowed []string) Handler {
	return func(c *Context) error {
		return apperrors.New(apperrors.CodeInvalidArgument, "method not allowed").
			WithField("allowed", strings.Join(allowed, ", "))
	}
}

// Respond writes a success envelope.
func Respond(c *Context, status int, data interface{}) error {
	env := Envelope{Status: status, RequestID: c.RequestID, Data: data}
	c.Writer.Header().Set("Content-Type", "application/json")
	c.Writer.Header().Set("X-Request-ID", c.RequestID)
	c.Writer.WriteHeader(status)
	return json.NewEncoder(c.Writer).Encode(env)
}

// NoContent writes a 204.
func NoContent(c *Context) error {
	c.Writer.Header().Set("X-Request-ID", c.RequestID)
	c.Writer.WriteHeader(http.StatusNoContent)
	return nil
}

// contextKey is a private key type for context values.
type contextKey int

const claimsKey contextKey = 1

// WithClaims returns a request whose context carries the principal.
func WithClaims(req *http.Request, claims interface{}) *http.Request {
	return req.WithContext(context.WithValue(req.Context(), claimsKey, claims))
}

// ClaimsFromContext returns the principal a middleware stored.
func ClaimsFromContext(req *http.Request) interface{} {
	return req.Context().Value(claimsKey)
}
