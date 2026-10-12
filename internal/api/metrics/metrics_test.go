package metrics

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
)

func TestCountersAccumulate(t *testing.T) {
	r := New()
	r.Incr("http_requests_total", map[string]string{"method": "GET", "route": "/health"})
	r.Incr("http_requests_total", map[string]string{"method": "GET", "route": "/health"})
	r.Add("http_requests_total", map[string]string{"method": "GET", "route": "/health"}, 3)

	got := scrape(t, r)
	if !strings.Contains(got, `http_requests_total{method="GET",route="/health"} 5`) {
		t.Fatalf("counter not accumulated:\n%s", got)
	}
}

func TestLabelsAreSortedAndEscaped(t *testing.T) {
	r := New()
	// Two keys in a deliberately unsorted order, and a value containing a
	// quote that would otherwise break out of the label.
	r.Incr("c", map[string]string{"route": "/health", "method": "GET"})
	got := scrape(t, r)
	if !strings.Contains(got, `c{method="GET",route="/health"} 1`) {
		t.Fatalf("labels not sorted:\n%s", got)
	}

	r2 := New()
	r2.Incr("c", map[string]string{"path": `a"b`})
	got2 := scrape(t, r2)
	if !strings.Contains(got2, `c{path="a\"b"} 1`) {
		t.Fatalf("a quote in a label value was not escaped:\n%s", got2)
	}
}

func TestGaugeSetAndGet(t *testing.T) {
	r := New()
	r.Set("queue_depth", "pending jobs", map[string]string{"queue": "ingest"}, 7)
	if got := r.Get("queue_depth", map[string]string{"queue": "ingest"}); got != 7 {
		t.Fatalf("gauge = %v, want 7", got)
	}
	r.Set("queue_depth", "pending jobs", map[string]string{"queue": "ingest"}, 2.5)
	if got := r.Get("queue_depth", map[string]string{"queue": "ingest"}); got != 2.5 {
		t.Fatalf("gauge = %v, want 2.5", got)
	}
	got := scrape(t, r)
	if !strings.Contains(got, `queue_depth{queue="ingest"} 2.5`) {
		t.Fatalf("gauge not rendered:\n%s", got)
	}
}

func TestHistogramBucketsAreCumulative(t *testing.T) {
	r := New()
	r.RegisterHistogram("http_request_duration_seconds", "d", defaultBuckets)
	labels := map[string]string{"method": "GET"}

	r.Observe("http_request_duration_seconds", labels, 0.2)
	r.Observe("http_request_duration_seconds", labels, 0.012)
	r.Observe("http_request_duration_seconds", labels, 3.0)

	got := scrape(t, r)
	// 0.012 lands in le=0.025; 0.2 in le=0.25; 3.0 in le=5. Cumulative, so
	// the later buckets include the earlier counts.
	for _, want := range []string{
		`http_request_duration_seconds_bucket{method="GET",le="0.025"} 1`,
		`http_request_duration_seconds_bucket{method="GET",le="0.25"} 2`,
		`http_request_duration_seconds_bucket{method="GET",le="5"} 3`,
		`http_request_duration_seconds_count{method="GET"} 3`,
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("missing %q in:\n%s", want, got)
		}
	}
}

func TestHistogramSumIsSeconds(t *testing.T) {
	r := New()
	r.RegisterHistogram("d", "d", []float64{1})
	r.Observe("d", nil, 0.5)
	r.Observe("d", nil, 1.5)
	got := scrape(t, r)
	if !strings.Contains(got, "d_sum 2") {
		t.Fatalf("sum not rendered:\n%s", got)
	}
}

// --- Bounded route labels --------------------------------------------------

func TestRouteTemplateBoundsTheLabel(t *testing.T) {
	// Without a template, one series per conversation id is created, which is
	// a memory leak disguised as a metric.
	r := New()
	r.RegisterPathTemplate("/conversations/{id}")
	r.RegisterPathTemplate("/conversations/{id}/messages")

	for _, p := range []string{
		"/conversations/abc", "/conversations/xyz",
		"/conversations/abc/messages", "/conversations/xyz/messages",
	} {
		if got := r.PathLabel(p); !strings.Contains(got, "{") {
			t.Fatalf("path %q mapped to %q, want a template", p, got)
		}
	}
}

func TestPathLabelFallsBackWhenUnknown(t *testing.T) {
	r := New()
	if got := r.PathLabel("/not-registered"); got != "/not-registered" {
		t.Fatalf("unknown path = %q, want the concrete path", got)
	}
}

func TestTemplateMatchingIsLengthAgnostic(t *testing.T) {
	// A missing or extra segment must not match, or {id} would swallow a
	// whole path.
	if matchesTemplate("/a/{id}", "/a/1/extra") {
		t.Fatal("a longer path matched a shorter template")
	}
	if !matchesTemplate("/a/{id}/b", "/a/1/b") {
		t.Fatal("an exact template did not match")
	}
	if matchesTemplate("/a/{id}", "/a/") {
		t.Fatal("an empty segment matched a wildcard")
	}
}

// --- Middleware ------------------------------------------------------------

func TestMiddlewareRecordsRateDurationAndErrors(t *testing.T) {
	r := New()
	r.RegisterPathTemplate("/ok")
	r.RegisterPathTemplate("/boom")

	h := Middleware(r)(http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		if req.URL.Path == "/boom" {
			w.WriteHeader(500)
			return
		}
		w.WriteHeader(200)
	}))

	for _, p := range []string{"/ok", "/ok", "/boom"} {
		req := httptest.NewRequest("GET", p, nil)
		h.ServeHTTP(httptest.NewRecorder(), req)
	}

	got := scrape(t, r)
	if !strings.Contains(got, `http_requests_total{method="GET",route="/ok"} 2`) {
		t.Fatalf("request rate not recorded:\n%s", got)
	}
	if !strings.Contains(got, `http_request_errors_total{method="GET",route="/boom"} 1`) {
		t.Fatalf("error rate not recorded:\n%s", got)
	}
	if !strings.Contains(got, "http_request_duration_seconds_count") {
		t.Fatalf("duration not recorded:\n%s", got)
	}
}

// --- Concurrency -----------------------------------------------------------

func TestConcurrentIncIsSafe(t *testing.T) {
	r := New()
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			r.Incr("http_requests_total", map[string]string{"method": "GET"})
			r.Observe("http_request_duration_seconds", nil, 0.01)
			r.Set("g", "d", nil, 1)
		}()
	}
	wg.Wait()

	got := scrape(t, r)
	if !strings.Contains(got, `http_requests_total{method="GET"} 100`) {
		t.Fatalf("counts lost under concurrency:\n%s", got)
	}
}

// --- Helpers ---------------------------------------------------------------

func scrape(t *testing.T, r *Registry) string {
	t.Helper()
	rec := httptest.NewRecorder()
	r.Handler().ServeHTTP(rec, httptest.NewRequest("GET", "/metrics", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("metrics status = %d", rec.Code)
	}
	return rec.Body.String()
}
