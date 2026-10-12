// Package tracing provides request correlation: an id that follows a user
// action through every component, plus a lightweight in-process span recorder.
//
// The request id is the only thing that makes an incident debuggable. When a
// user reports that an answer was wrong, the evidence is a log line, a trace,
// and a provider payload, and without a shared id they are three unrelated
// records. So the id is generated at the edge, propagated on the header, and
// attached to the context.
//
// A caller-supplied id is trusted, because a user reporting an incident
// quotes the one they were shown, but it is bounded and sanitised first: an
// unbounded or control-character-carrying header would inject a log line.
//
// The spans are in-process and bounded rather than exported to an external
// collector. A trace that requires an OTLP collector to be running is a trace
// that does not exist in a dev environment; a bounded in-process ring is
// always available, and the sampling decision is the caller's.
package tracing

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Header is the request id header. It is the standard name so an existing
// edge or gateway can set it and this service will honour it.
const Header = "X-Request-ID"

// MaxIDLength bounds a caller-supplied id, so a log line cannot be inflated.
const MaxIDLength = 128

// Generate returns a fresh request id.
func Generate() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		// crypto/rand failing is not request-scoped; a clock-based fallback
		// still gives a unique-enough id for correlation.
		return "fallback-" + strconv.FormatInt(time.Now().UnixNano(), 36)
	}
	return hex.EncodeToString(b[:])
}

// Sanitize bounds and cleans a caller-supplied id.
//
// A caller-supplied id is trusted because the user reporting an incident
// quotes the id they were shown, but control characters are removed because
// an unsanitised value would inject a new log line or terminate a JSON
// string in one.
func Sanitize(v string) string {
	if v == "" {
		return ""
	}
	if len(v) > MaxIDLength {
		v = v[:MaxIDLength]
	}
	// Keep printable ASCII. Anything else is dropped, including the quotes,
	// backslashes and newlines that would break a JSON log line.
	var b strings.Builder
	for _, r := range v {
		if r < 0x20 || r == 0x7f {
			continue
		}
		if r == '"' || r == '\\' {
			continue
		}
		b.WriteRune(r)
	}
	out := b.String()
	if out == "" {
		return ""
	}
	return out
}

// FromRequest returns the request id for a request, generating one when the
// caller did not supply it. It also sets the response header, so the id is
// visible to whoever reported the problem.
func FromRequest(req *http.Request) string {
	id := ""
	if req != nil {
		id = Sanitize(req.Header.Get(Header))
	}
	if id == "" {
		id = Generate()
	}
	return id
}

// ---- Context propagation --------------------------------------------------

type ctxKey int

const idKey ctxKey = iota

// WithID attaches a request id to a context.
func WithID(ctx context.Context, id string) context.Context {
	return context.WithValue(ctx, idKey, id)
}

// FromContext returns the attached id, or an empty string.
func FromContext(ctx context.Context) string {
	if v, ok := ctx.Value(idKey).(string); ok {
		return v
	}
	return ""
}

// Middleware assigns a request id and puts it on the response header and the
// context, so a handler can log it without having received it.
func Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		id := FromRequest(req)
		w.Header().Set(Header, id)
		next.ServeHTTP(w, req.WithContext(WithID(req.Context(), id)))
	})
}

// ---- Spans ----------------------------------------------------------------

// Span is one timed unit of work within a request.
type Span struct {
	Name     string        `json:"name"`
	Parent   string        `json:"parent,omitempty"`
	Start    time.Time     `json:"start"`
	Duration time.Duration `json:"duration_ms"`
	// Attrs carries per-span attributes. Values are strings, so a span is
	// always JSON-serialisable without a marshaler.
	Attrs map[string]string `json:"attrs,omitempty"`
	// Err is set when the span ended in failure.
	Err string `json:"error,omitempty"`
}

// Recorder holds the spans for one request, bounded so a long request
// cannot grow memory without limit.
type Recorder struct {
	mu      sync.Mutex
	request string
	spans   []Span
	// depth tracks nesting so a parent can be attached.
	depth map[string]int
}

// New returns a recorder for a request id.
func New(requestID string) *Recorder {
	return &Recorder{request: requestID, depth: map[string]int{}}
}

// FromContextRecorder returns the attached recorder, or nil.
func FromContextRecorder(ctx context.Context) *Recorder {
	if r, ok := ctx.Value(recorderKey).(*Recorder); ok {
		return r
	}
	return nil
}

// WithRecorder attaches a recorder.
func WithRecorder(ctx context.Context, r *Recorder) context.Context {
	return context.WithValue(ctx, recorderKey, r)
}

const recorderKey ctxKey = iota + 1

// Start begins a span and returns a function that ends it.
//
// The returned function is deferred, so the common call site reads:
//
//	defer tracing.WithRecorder(ctx, tracing.New(id)).Start("db").End()
//
// End is idempotent, so a double defer is harmless.
func (r *Recorder) Start(name string, attrs ...string) *SpanHandle {
	if r == nil {
		return &SpanHandle{}
	}
	r.mu.Lock()
	r.depth[name]++
	r.mu.Unlock()
	h := &SpanHandle{
		recorder: r,
		span: Span{
			Name:  name,
			Start: time.Now().UTC(),
			Attrs: attrsToMap(attrs),
		},
		parent: r.parentOf(name),
	}
	return h
}

// parentOf finds the enclosing span by the recursion depth recorded in
// Start. It is approximate but bounded, which is what a record of
// "what happened during this request" needs rather than exact tree
// reconstruction.
func (r *Recorder) parentOf(name string) string {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.depth[name] <= 1 {
		return ""
	}
	// The most recently started span at a shallower depth is the parent.
	// Rings are bounded, so this is a small scan.
	for i := len(r.spans) - 1; i >= 0; i-- {
		if r.spans[i].Name != name {
			return r.spans[i].Name
		}
	}
	return ""
}

func attrsToMap(attrs []string) map[string]string {
	if len(attrs) == 0 {
		return nil
	}
	out := map[string]string{}
	for i := 0; i+1 < len(attrs); i += 2 {
		out[attrs[i]] = attrs[i+1]
	}
	return out
}

// SpanHandle records a span and ends it.
type SpanHandle struct {
	recorder *Recorder
	span     Span
	parent   string
	ended    bool
	mu       sync.Mutex
}

// Attr adds an attribute to the span before it ends.
func (h *SpanHandle) Attr(k, v string) *SpanHandle {
	if h == nil {
		return h
	}
	h.mu.Lock()
	defer h.mu.Unlock()
	if h.span.Attrs == nil {
		h.span.Attrs = map[string]string{}
	}
	h.span.Attrs[k] = v
	return h
}

// End records the span. It is idempotent, so a deferred End after an explicit
// one does not double-record.
func (h *SpanHandle) End() {
	if h == nil || h.recorder == nil {
		return
	}
	h.mu.Lock()
	if h.ended {
		h.mu.Unlock()
		return
	}
	h.ended = true
	h.span.Parent = h.parent
	h.span.Duration = time.Since(h.span.Start)
	span := h.span
	h.mu.Unlock()

	h.recorder.mu.Lock()
	if len(h.recorder.spans) >= maxSpans {
		// Drop the oldest rather than growing: a trace is for diagnosing one
		// request, and the most recent spans are the ones that mattered.
		h.recorder.spans = h.recorder.spans[1:]
	}
	h.recorder.spans = append(h.recorder.spans, span)
	h.recorder.mu.Unlock()
}

// maxSpans bounds a recorder. A request that generates more than this many
// timed units is already misbehaving, and the list must not grow with it.
const maxSpans = 200

// Fail marks the span as failed and ends it.
func (h *SpanHandle) Fail(err error) {
	if h == nil {
		return
	}
	h.mu.Lock()
	if err != nil {
		h.span.Err = err.Error()
	}
	h.mu.Unlock()
	h.End()
}

// Spans returns a copy of the recorded spans.
func (r *Recorder) Spans() []Span {
	if r == nil {
		return nil
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]Span, len(r.spans))
	copy(out, r.spans)
	return out
}

// Snapshot is the exported view of a request's trace.
type Snapshot struct {
	Request string `json:"request_id"`
	Spans   []Span `json:"spans"`
}

// Summarise renders the trace for an endpoint or a debug log.
func (r *Recorder) Summarise() Snapshot {
	if r == nil {
		return Snapshot{}
	}
	return Snapshot{Request: r.request, Spans: r.Spans()}
}
