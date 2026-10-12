package tracing

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestGenerateIsHexOfTheRightLength(t *testing.T) {
	id := Generate()
	if len(id) != 32 {
		t.Fatalf("id length = %d, want 32", len(id))
	}
	for _, r := range id {
		if !strings.ContainsRune("0123456789abcdef", r) {
			t.Fatalf("id is not hex: %q", id)
		}
	}
}

func TestGenerateIsUnique(t *testing.T) {
	seen := map[string]bool{}
	for i := 0; i < 500; i++ {
		id := Generate()
		if seen[id] {
			t.Fatalf("duplicate id generated: %q", id)
		}
		seen[id] = true
	}
}

func TestSanitizeRemovesLogInjectingCharacters(t *testing.T) {
	// A newline or a quote in an id would break a JSON log line or start a
	// forged one.
	for _, raw := range []string{
		"abc\n{\"level\":\"error\"}",
		`abc"injected`,
		`abc\\escaped`,
		"tab\there",
		"ctrl\x01\x02",
	} {
		got := Sanitize(raw)
		if strings.ContainsAny(got, "\n\"\\\t") {
			t.Fatalf("Sanitize(%q) = %q, kept a log-injecting character", raw, got)
		}
		for _, r := range got {
			if r < 0x20 || r == 0x7f {
				t.Fatalf("Sanitize(%q) = %q, kept a control character", raw, got)
			}
		}
	}
}

func TestSanitizeBoundsLength(t *testing.T) {
	got := Sanitize(strings.Repeat("a", 1000))
	if len(got) > MaxIDLength {
		t.Fatalf("id length = %d, want at most %d", len(got), MaxIDLength)
	}
}

func TestSanitizeReturnsEmptyForAnUnusableValue(t *testing.T) {
	// A value that is entirely control characters must not produce a
	// non-empty id of unknown provenance.
	if got := Sanitize("\n\r\t"); got != "" {
		t.Fatalf("Sanitize(control only) = %q, want empty", got)
	}
}

func TestFromRequestHonoursACallerID(t *testing.T) {
	req := httptest.NewRequest("GET", "/x", nil)
	req.Header.Set(Header, "user-supplied-trace")
	if got := FromRequest(req); got != "user-supplied-trace" {
		t.Fatalf("id = %q, want the caller's", got)
	}
}

func TestFromRequestGeneratesWhenAbsent(t *testing.T) {
	req := httptest.NewRequest("GET", "/x", nil)
	if got := FromRequest(req); len(got) != 32 {
		t.Fatalf("id = %q, want a generated one", got)
	}
}

func TestMiddlewareSetsTheHeaderAndContext(t *testing.T) {
	var seen string
	h := Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen = FromContext(r.Context())
		w.WriteHeader(200)
	}))

	req := httptest.NewRequest("GET", "/x", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Header().Get(Header) == "" {
		t.Fatal("no request id on the response")
	}
	if seen == "" {
		t.Fatal("the handler could not read the request id from its context")
	}
	if seen != rec.Header().Get(Header) {
		t.Fatalf("context id %q != header id %q", seen, rec.Header().Get(Header))
	}
}

func TestContextReturnsEmptyWithoutOne(t *testing.T) {
	if got := FromContext(context.Background()); got != "" {
		t.Fatalf("id = %q, want empty", got)
	}
}

// ---- Spans ----------------------------------------------------------------

func TestSpansRecordNameAndDuration(t *testing.T) {
	r := New("req-1")
	h := r.Start("db.query")
	time.Sleep(2 * time.Millisecond)
	h.End()

	spans := r.Spans()
	if len(spans) != 1 {
		t.Fatalf("%d spans, want 1", len(spans))
	}
	if spans[0].Name != "db.query" {
		t.Fatalf("span name = %q", spans[0].Name)
	}
}

func TestEndIsIdempotent(t *testing.T) {
	r := New("req")
	h := r.Start("work")
	h.End()
	h.End()
	if len(r.Spans()) != 1 {
		t.Fatalf("%d spans after a double End, want 1", len(r.Spans()))
	}
}

func TestAttrIsRecorded(t *testing.T) {
	r := New("req")
	h := r.Start("http.call").Attr("status", "200").Attr("bytes", "4096")
	h.End()
	spans := r.Spans()
	if len(spans) != 1 {
		t.Fatalf("%d spans", len(spans))
	}
	if spans[0].Attrs["status"] != "200" || spans[0].Attrs["bytes"] != "4096" {
		t.Fatalf("attrs = %v", spans[0].Attrs)
	}
}

func TestFailRecordsTheError(t *testing.T) {
	r := New("req")
	r.Start("provider.call").Fail(context.DeadlineExceeded)
	spans := r.Spans()
	if len(spans) != 1 || spans[0].Err == "" {
		t.Fatal("the error was not recorded on the span")
	}
	if spans[0].Err != "context deadline exceeded" {
		t.Fatalf("err = %q", spans[0].Err)
	}
}

func TestSpansAreBounded(t *testing.T) {
	// A request that generates thousands of timed units must not grow the
	// recorder without limit.
	r := New("req")
	for i := 0; i < maxSpans+100; i++ {
		r.Start("step").End()
	}
	if got := len(r.Spans()); got > maxSpans {
		t.Fatalf("%d spans retained with a bound of %d", got, maxSpans)
	}
	if got := len(r.Spans()); got != maxSpans {
		t.Fatalf("%d spans retained, want exactly %d (oldest dropped)", got, maxSpans)
	}
}

func TestSpansReturnACopy(t *testing.T) {
	r := New("req")
	r.Start("x").End()
	spans := r.Spans()
	spans[0].Name = "mutated"
	if r.Spans()[0].Name == "mutated" {
		t.Fatal("mutating the returned slice corrupted the recorder")
	}
}

func TestSummariseCarriesTheRequestID(t *testing.T) {
	r := New("req-42")
	r.Start("x").End()
	snap := r.Summarise()
	if snap.Request != "req-42" {
		t.Fatalf("request = %q", snap.Request)
	}
	if len(snap.Spans) != 1 {
		t.Fatalf("%d spans in the snapshot", len(snap.Spans))
	}
}

func TestNilRecorderIsSafe(t *testing.T) {
	// A nil recorder happens when a handler runs without the middleware, and
	// it must not panic.
	var r *Recorder
	r.Start("x").End()
	r.Start("y").Attr("k", "v").Fail(nil)
	if got := len(r.Spans()); got != 0 {
		t.Fatalf("%d spans from a nil recorder", got)
	}
}

func TestConcurrentSpansAreSafe(t *testing.T) {
	r := New("req")
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			r.Start("work").Attr("k", "v").End()
		}()
	}
	wg.Wait()
	if len(r.Spans()) == 0 {
		t.Fatal("no spans recorded under concurrency")
	}
}
