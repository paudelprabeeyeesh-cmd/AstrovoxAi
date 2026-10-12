// Package metrics provides the Prometheus text exposition for the Go API.
//
// Four golden signals are instrumented by name because those are the ones an
// on-call engineer asks about during an incident: request rate, request
// duration, error rate, and saturation. Everything else is derived.
//
// The registry is hand-written rather than pulled from a dependency, for the
// same reason the rest of this repo uses the standard library: a metrics
// library is a transitive dependency in every service, and the exposition
// format is a few dozen lines.
//
// Label discipline matters more than the volume. request_count carries
// method, path, and status as a template path (/conversations/{id}, not the
// concrete id), because an unbounded label value is a memory leak: one
// series per conversation id ever created.
package metrics

import (
	"fmt"
	"math"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// Registry holds counters, gauges and histograms.
type Registry struct {
	mu sync.RWMutex

	// counters is keyed by name+"|"+sortedLabels.
	counters map[string]*counter
	// gauges is keyed the same way.
	gauges map[string]*gauge
	// histograms is keyed by name+"|"+sortedLabels.
	histograms map[string]*histogram

	// pathTemplates maps a concrete path back to its route template, so a
	// label value stays bounded.
	pathTemplates sync.Map
}

type counter struct {
	desc   string
	values sync.Map // labels -> *atomic.Int64
}

type gauge struct {
	desc   string
	values sync.Map
}

type histogram struct {
	desc    string
	buckets []float64
	values  sync.Map // labels -> *histValue
}

type histValue struct {
	sum   atomic.Int64 // micros, to keep the value integral
	count atomic.Int64
	// bucketCounts[i] is the cumulative count for buckets[i].
	bucketCounts []atomic.Int64
}

// New returns an empty registry with the HTTP histograms pre-registered, so
// observing before the first scrape is not a silent loss.
func New() *Registry {
	r := &Registry{
		counters:   map[string]*counter{},
		gauges:     map[string]*gauge{},
		histograms: map[string]*histogram{},
	}
	r.RegisterHistogram(
		"http_request_duration_seconds",
		"HTTP request duration in seconds, by method and route template.",
		defaultBuckets,
	)
	r.describeCounter("http_requests_total", "Total HTTP requests, by method, route template and status.")
	r.describeCounter("http_request_errors_total", "HTTP responses with a 5xx status.")
	return r
}

// describe registers a counter if it is not already known.
func (r *Registry) describeCounter(name, desc string) *counter {
	r.mu.RLock()
	c, ok := r.counters[name]
	r.mu.RUnlock()
	if ok {
		return c
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if c, ok := r.counters[name]; ok {
		return c
	}
	c = &counter{desc: desc}
	r.counters[name] = c
	return c
}

// RegisterPathTemplate teaches the registry the route template for a path,
// so a bounded label can be used in place of a concrete id.
func (r *Registry) RegisterPathTemplate(template string) {
	r.pathTemplates.Store(template, true)
}

// PathLabel returns the template for a concrete path, or the path itself
// when no template is known. Returning the concrete path is a fallback, not a
// default: it is bounded by the pages a deployment actually serves.
func (r *Registry) PathLabel(path string) string {
	var best string
	r.pathTemplates.Range(func(k, _ any) bool {
		t := k.(string)
		if matchesTemplate(t, path) && len(t) > len(best) {
			best = t
		}
		return true
	})
	if best != "" {
		return best
	}
	return path
}

// matchesTemplate reports whether a concrete path matches a template, so the
// most specific known template wins.
func matchesTemplate(template, path string) bool {
	tParts := strings.Split(template, "/")
	pParts := strings.Split(path, "/")
	if len(tParts) != len(pParts) {
		return false
	}
	for i := range tParts {
		if strings.HasPrefix(tParts[i], "{") && strings.HasSuffix(tParts[i], "}") {
			if pParts[i] == "" {
				return false
			}
			continue
		}
		if tParts[i] != pParts[i] {
			return false
		}
	}
	return true
}

// Incr adds one to a counter.
func (r *Registry) Incr(name string, labels map[string]string) {
	r.Add(name, labels, 1)
}

// Add adds a delta to a counter. Metric names are the standard ones so a
// dashboard written for this service does not need a translation table.
func (r *Registry) Add(name string, labels map[string]string, delta int64) {
	var desc string
	switch name {
	case "http_requests_total":
		desc = "Total HTTP requests, by method, route template and status."
	case "http_request_errors_total":
		desc = "HTTP responses with a 5xx status."
	default:
		desc = name
	}
	c := r.describeCounter(name, desc)
	key := encodeLabels(labels)
	v, _ := c.values.LoadOrStore(key, &atomic.Int64{})
	v.(*atomic.Int64).Add(delta)
}

// Set writes a gauge.
func (r *Registry) Set(name, desc string, labels map[string]string, value float64) {
	r.mu.RLock()
	g, ok := r.gauges[name]
	r.mu.RUnlock()
	if !ok {
		r.mu.Lock()
		if g, ok = r.gauges[name]; !ok {
			g = &gauge{desc: desc}
			r.gauges[name] = g
		}
		r.mu.Unlock()
	}
	key := encodeLabels(labels)
	v, _ := g.values.LoadOrStore(key, &atomic.Int64{})
	// Store as bits of a float64 so the value is exact.
	v.(*atomic.Int64).Store(int64(math.Float64bits(value)))
}

// Get reads a gauge.
func (r *Registry) Get(name string, labels map[string]string) float64 {
	r.mu.RLock()
	g, ok := r.gauges[name]
	r.mu.RUnlock()
	if !ok {
		return 0
	}
	v, ok := g.values.Load(encodeLabels(labels))
	if !ok {
		return 0
	}
	return math.Float64frombits(uint64(v.(*atomic.Int64).Load()))
}

// RegisterHistogram declares a histogram with buckets.
func (r *Registry) RegisterHistogram(name, desc string, buckets []float64) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.histograms[name]; ok {
		return
	}
	h := &histogram{desc: desc, buckets: append([]float64{}, buckets...)}
	r.histograms[name] = h
}

// Observe records a duration against a histogram.
func (r *Registry) Observe(name string, labels map[string]string, seconds float64) {
	r.mu.RLock()
	h, ok := r.histograms[name]
	r.mu.RUnlock()
	if !ok {
		return
	}
	key := encodeLabels(labels)
	v, _ := h.values.LoadOrStore(key, &histValue{
		bucketCounts: make([]atomic.Int64, len(h.buckets)),
	})
	hv := v.(*histValue)
	hv.sum.Add(int64(seconds * 1e6))
	hv.count.Add(1)
	for i, b := range h.buckets {
		if seconds <= b {
			hv.bucketCounts[i].Add(1)
		}
	}
}

// defaultBuckets are seconds, spanning sub-millisecond to a minute, which is
// the range an LLM-backed endpoint actually occupies.
var defaultBuckets = []float64{
	0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0,
}

// Handler returns an http.Handler that renders the exposition format.
func (r *Registry) Handler() http.Handler {
	r.RegisterHistogram(
		"http_request_duration_seconds",
		"HTTP request duration in seconds, by method and route template.",
		defaultBuckets,
	)
	r.describeCounter("http_requests_total", "Total HTTP requests.")
	r.describeCounter("http_request_errors_total", "HTTP 5xx responses.")

	return http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
		r.render(w)
	})
}

// render writes the exposition format. It is a single pass, so a scrape
// cannot observe a half-written series.
func (r *Registry) render(w http.ResponseWriter) {
	r.mu.RLock()
	names := make([]string, 0, len(r.counters))
	for n := range r.counters {
		names = append(names, n)
	}
	r.mu.RUnlock()
	sort.Strings(names)

	for _, name := range names {
		r.mu.RLock()
		c := r.counters[name]
		r.mu.RUnlock()
		fmt.Fprintf(w, "# HELP %s %s\n# TYPE %s counter\n", name, c.desc, name)
		c.values.Range(func(k, v any) bool {
			fmt.Fprintf(w, "%s%s %d\n", name, k.(string), v.(*atomic.Int64).Load())
			return true
		})
	}

	r.mu.RLock()
	gNames := make([]string, 0, len(r.gauges))
	for n := range r.gauges {
		gNames = append(gNames, n)
	}
	hNames := make([]string, 0, len(r.histograms))
	for n := range r.histograms {
		hNames = append(hNames, n)
	}
	r.mu.RUnlock()
	sort.Strings(gNames)
	sort.Strings(hNames)

	for _, name := range gNames {
		r.mu.RLock()
		g := r.gauges[name]
		r.mu.RUnlock()
		fmt.Fprintf(w, "# HELP %s %s\n# TYPE %s gauge\n", name, g.desc, name)
		g.values.Range(func(k, v any) bool {
			val := math.Float64frombits(uint64(v.(*atomic.Int64).Load()))
			fmt.Fprintf(w, "%s%s %s\n", name, k.(string), strconv.FormatFloat(val, 'f', -1, 64))
			return true
		})
	}

	for _, name := range hNames {
		r.mu.RLock()
		h := r.histograms[name]
		r.mu.RUnlock()
		fmt.Fprintf(w, "# HELP %s %s\n# TYPE %s histogram\n", name, h.desc, name)
		h.values.Range(func(k, v any) bool {
			hv := v.(*histValue)
			// The le label belongs inside the same braces as the others, so
			// the label set is combined rather than concatenated.
			labels := k.(string)
			for i := range h.buckets {
				inner := strings.TrimSuffix(labels, "}")
				if inner != "" {
					inner += ","
				}
				inner += `le="` + strconv.FormatFloat(h.buckets[i], 'f', -1, 64) + `"}`
				fmt.Fprintf(w, "%s_bucket%s %d\n", name, inner, hv.bucketCounts[i].Load())
			}
			fmt.Fprintf(w, "%s_count%s %d\n", name, labels, hv.count.Load())
			fmt.Fprintf(w, "%s_sum%s %s\n", name, labels,
				strconv.FormatFloat(float64(hv.sum.Load())/1e6, 'f', -1, 64))
			return true
		})
	}
}

// encodeLabels renders labels in the sorted "k=\"v\"" form the exposition
// format requires.
func encodeLabels(labels map[string]string) string {
	if len(labels) == 0 {
		return ""
	}
	keys := make([]string, 0, len(labels))
	for k := range labels {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	var b strings.Builder
	b.WriteString("{")
	for i, k := range keys {
		if i > 0 {
			b.WriteString(",")
		}
		b.WriteString(k)
		b.WriteString(`="`)
		// Escape so a value cannot break out of the label and inject a
		// spurious series.
		b.WriteString(escapeLabel(labels[k]))
		b.WriteString(`"`)
	}
	b.WriteString("}")
	return b.String()
}

func escapeLabel(v string) string {
	v = strings.ReplaceAll(v, `\`, `\\`)
	v = strings.ReplaceAll(v, `"`, `\"`)
	v = strings.ReplaceAll(v, "\n", `\n`)
	return v
}

// Middleware records request rate, duration and errors with a bounded route
// template as the label. It is the one place all three are recorded, so a
// new endpoint is instrumented by being routed.
func Middleware(r *Registry) func(next http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
			start := time.Now()
			rec := &statusRecorder{ResponseWriter: w, status: 200}
			next.ServeHTTP(rec, req)

			labels := map[string]string{
				"method": req.Method,
				"route":  r.PathLabel(req.URL.Path),
			}
			r.Incr("http_requests_total", labels)
			r.Observe("http_request_duration_seconds", labels, time.Since(start).Seconds())
			if rec.status >= 500 {
				r.Incr("http_request_errors_total", labels)
			}
		})
	}
}

// statusRecorder captures the status code without buffering the body.
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
