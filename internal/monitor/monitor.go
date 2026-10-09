// Package monitor provides a monitoring dashboard: metrics registry,
// time series, health checks, alerting and HTML/text rendering.
package monitor

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// MetricType identifies a metric kind.
type MetricType int

const (
	Counter MetricType = iota
	Gauge
	MetricHistogram
)

func (m MetricType) String() string {
	switch m {
	case Counter:
		return "counter"
	case Gauge:
		return "gauge"
	case MetricHistogram:
		return "histogram"
	default:
		return "unknown"
	}
}

// Metric is a single metric.
type Metric struct {
	Name    string
	Type    MetricType
	Labels  map[string]string
	help    string
	counter atomic.Int64
	gauge   atomic.Int64
	hist    *Histogram
}

// Histogram tracks distribution of observations.
type Histogram struct {
	Count   atomic.Int64
	Sum     atomic.Int64 // sum stored as bits of float64
	buckets []float64
	counts  []atomic.Int64
}

// NewHistogram creates a histogram with the given buckets.
func NewHistogram(buckets []float64) *Histogram {
	return &Histogram{
		buckets: append([]float64(nil), buckets...),
		counts:  make([]atomic.Int64, len(buckets)+1),
	}
}

// Observe records an observation.
func (h *Histogram) Observe(v float64) {
	h.Count.Add(1)
	for i, b := range h.buckets {
		if v <= b {
			h.counts[i].Add(1)
		}
	}
	h.counts[len(h.buckets)].Add(1)
}

// Count returns the observation count.
func (h *Histogram) CountValue() int64 { return h.Count.Load() }

// Registry holds all metrics.
type Registry struct {
	mu      sync.RWMutex
	metrics map[string]*Metric
}

// NewRegistry creates a metrics registry.
func NewRegistry() *Registry {
	r := &Registry{metrics: make(map[string]*Metric)}
	r.registerRuntimeMetrics()
	return r
}

func key(name string, labels map[string]string) string {
	if len(labels) == 0 {
		return name
	}
	keys := make([]string, 0, len(labels))
	for k := range labels {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	var sb strings.Builder
	sb.WriteString(name)
	sb.WriteString("{")
	for i, k := range keys {
		if i > 0 {
			sb.WriteString(",")
		}
		sb.WriteString(k)
		sb.WriteString(`="`)
		sb.WriteString(labels[k])
		sb.WriteString(`"`)
	}
	sb.WriteString("}")
	return sb.String()
}

// Register registers a metric.
func (r *Registry) Register(name string, typ MetricType, help string, labels map[string]string) *Metric {
	r.mu.Lock()
	defer r.mu.Unlock()
	k := key(name, labels)
	if m, ok := r.metrics[k]; ok {
		return m
	}
	m := &Metric{Name: name, Type: typ, Labels: cloneLabels(labels), help: help}
	if typ == MetricHistogram {
		m.hist = NewHistogram([]float64{0.001, 0.01, 0.1, 1, 10})
	}
	r.metrics[k] = m
	return m
}

func cloneLabels(l map[string]string) map[string]string {
	if len(l) == 0 {
		return nil
	}
	out := make(map[string]string, len(l))
	for k, v := range l {
		out[k] = v
	}
	return out
}

// Inc increments a counter metric.
func (r *Registry) Inc(name string, labels map[string]string, n int64) {
	m := r.Register(name, Counter, "", labels)
	m.counter.Add(n)
}

// Set sets a gauge metric.
func (r *Registry) Set(name string, labels map[string]string, v int64) {
	m := r.Register(name, Gauge, "", labels)
	m.gauge.Store(v)
}

// Observe observes a histogram metric.
func (r *Registry) Observe(name string, labels map[string]string, v float64) {
	m := r.Register(name, MetricHistogram, "", labels)
	if m.hist != nil {
		m.hist.Observe(v)
	}
}

// Get returns a metric.
func (r *Registry) Get(name string, labels map[string]string) (*Metric, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	m, ok := r.metrics[key(name, labels)]
	return m, ok
}

// Value returns the metric's current value.
func (m *Metric) Value() int64 {
	switch m.Type {
	case Counter:
		return m.counter.Load()
	case Gauge:
		return m.gauge.Load()
	case MetricHistogram:
		if m.hist != nil {
			return m.hist.Count.Load()
		}
	}
	return 0
}

// Snapshot renders all metrics as text.
func (r *Registry) Snapshot() string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	keys := make([]string, 0, len(r.metrics))
	for k := range r.metrics {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	var sb strings.Builder
	for _, k := range keys {
		m := r.metrics[k]
		sb.WriteString(fmt.Sprintf("%s %s = %d\n", m.Type, k, m.Value()))
	}
	return sb.String()
}

func (r *Registry) registerRuntimeMetrics() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.metrics[key("process_start_time_seconds", nil)] = &Metric{
		Name: "process_start_time_seconds", Type: Gauge,
	}
	r.metrics[key("go_uptime_seconds", nil)] = &Metric{
		Name: "go_uptime_seconds", Type: Gauge,
	}
	r.metrics["go_uptime_seconds"].gauge.Store(0)
}

// HealthStatus is a component's health state.
type HealthStatus string

const (
	StatusUp      HealthStatus = "up"
	StatusDown    HealthStatus = "down"
	StatusDegraded HealthStatus = "degraded"
)

// Component is a monitored component.
type Component struct {
	Name        string
	Status      HealthStatus
	Description string
	CheckedAt   time.Time
}

// Monitor is the top-level monitoring system.
type Monitor struct {
	registry *Registry
	mu       sync.RWMutex
	components map[string]*Component
	alerts    []Alert
	rules     []AlertRule
	started   time.Time
}

// NewMonitor creates a monitor.
func NewMonitor() *Monitor {
	return &Monitor{
		registry:   NewRegistry(),
		components: make(map[string]*Component),
		started:    time.Now(),
	}
}

// Registry returns the metrics registry.
func (m *Monitor) Registry() *Registry { return m.registry }

// RegisterComponent registers a monitored component.
func (m *Monitor) RegisterComponent(name, desc string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.components[name] = &Component{
		Name: name, Description: desc, Status: StatusUp, CheckedAt: time.Now(),
	}
}

// SetComponentStatus updates a component's status.
func (m *Monitor) SetComponentStatus(name string, s HealthStatus) {
	m.mu.Lock()
	defer m.mu.Unlock()
	c, ok := m.components[name]
	if !ok {
		c = &Component{Name: name}
		m.components[name] = c
	}
	c.Status = s
	c.CheckedAt = time.Now()
}

// Health returns the health of all components.
func (m *Monitor) Health() map[string]HealthStatus {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make(map[string]HealthStatus, len(m.components))
	for n, c := range m.components {
		out[n] = c.Status
	}
	return out
}

// IsHealthy returns whether all components are up or degraded.
func (m *Monitor) IsHealthy() bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	for _, c := range m.components {
		if c.Status == StatusDown {
			return false
		}
	}
	return true
}

// Alert is a fired alert.
type Alert struct {
	Name      string
	Message   string
	Severity  string
	FiredAt   time.Time
	Resolved  bool
}

// AlertRule defines a threshold-based alert.
type AlertRule struct {
	Name       string
	Metric     string
	Threshold  int64
	Severity   string
	Compare    string // "gt" or "lt"
	firing     bool
}

// AddRule registers an alert rule.
func (m *Monitor) AddRule(r AlertRule) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.rules = append(m.rules, r)
}

// Evaluate checks all alert rules.
func (m *Monitor) Evaluate() []Alert {
	m.mu.Lock()
	defer m.mu.Unlock()
	var fired []Alert
	now := time.Now()
	for i := range m.rules {
		r := &m.rules[i]
		metric, ok := m.registry.Get(r.Metric, nil)
		if !ok {
			continue
		}
		v := metric.Value()
		triggered := false
		switch r.Compare {
		case "lt":
			triggered = v < r.Threshold
		default:
			triggered = v > r.Threshold
		}
		if triggered && !r.firing {
			r.firing = true
			a := Alert{
				Name:     r.Name,
				Message:  fmt.Sprintf("%s %s %d (current %d)", r.Metric, compareText(r.Compare), r.Threshold, v),
				Severity: r.Severity,
				FiredAt:  now,
			}
			m.alerts = append(m.alerts, a)
			fired = append(fired, a)
		} else if !triggered && r.firing {
			r.firing = false
		}
	}
	return fired
}

func compareText(op string) string {
	if op == "lt" {
		return "below"
	}
	return "above"
}

// Alerts returns all alerts.
func (m *Monitor) Alerts() []Alert {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return append([]Alert(nil), m.alerts...)
}

// Series is a named time series.
type Series struct {
	Name      string
	Points    []Point
	MaxPoints int
	mu        sync.Mutex
}

// Point is a timestamped value.
type Point struct {
	Timestamp time.Time
	Value     float64
}

// NewSeries creates a series with a bounded window.
func NewSeries(name string, maxPoints int) *Series {
	return &Series{Name: name, MaxPoints: maxPoints}
}

// Add appends a point.
func (s *Series) Add(v float64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Points = append(s.Points, Point{Timestamp: time.Now(), Value: v})
	if s.MaxPoints > 0 && len(s.Points) > s.MaxPoints {
		s.Points = s.Points[len(s.Points)-s.MaxPoints:]
	}
}

// Latest returns the newest point.
func (s *Series) Latest() (Point, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.Points) == 0 {
		return Point{}, false
	}
	return s.Points[len(s.Points)-1], true
}

// Mean returns the average of all points.
func (s *Series) Mean() float64 {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.Points) == 0 {
		return 0
	}
	var sum float64
	for _, p := range s.Points {
		sum += p.Value
	}
	return sum / float64(len(s.Points))
}

// RenderDashboard renders an HTML dashboard.
func (m *Monitor) RenderDashboard() string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	var sb strings.Builder
	sb.WriteString("<!DOCTYPE html><html><head><title>Astrovox Monitor</title></head><body>\n")
	sb.WriteString("<h1>Astrovox AI Monitor</h1>\n")
	sb.WriteString(fmt.Sprintf("<p>Uptime: %s</p>\n", time.Since(m.started).Round(time.Second)))
	sb.WriteString("<h2>Health</h2><ul>\n")
	names := make([]string, 0, len(m.components))
	for n := range m.components {
		names = append(names, n)
	}
	sort.Strings(names)
	for _, n := range names {
		c := m.components[n]
		sb.WriteString(fmt.Sprintf("<li>%s: <b>%s</b> (%s)</li>\n", n, c.Status, c.Description))
	}
	sb.WriteString("</ul>\n<h2>Metrics</h2><pre>\n")
	sb.WriteString(m.registry.Snapshot())
	sb.WriteString("</pre>\n</body></html>\n")
	return sb.String()
}

// RenderText renders a plain-text dashboard.
func (m *Monitor) RenderText() string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	var sb strings.Builder
	sb.WriteString("Astrovox AI Monitor\n")
	sb.WriteString(fmt.Sprintf("Uptime: %s\n", time.Since(m.started).Round(time.Second)))
	sb.WriteString(fmt.Sprintf("Healthy: %v\n", m.IsHealthy()))
	sb.WriteString("\nMetrics:\n")
	sb.WriteString(m.registry.Snapshot())
	return sb.String()
}

// DashboardData returns a compact summary for external UIs.
func (m *Monitor) DashboardData() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()
	health := make(map[string]string, len(m.components))
	for n, c := range m.components {
		health[n] = string(c.Status)
	}
	return map[string]interface{}{
		"uptime_seconds": time.Since(m.started).Seconds(),
		"healthy":        m.isHealthyLocked(),
		"health":         health,
		"alerts":         len(m.alerts),
		"metrics":        len(m.registry.metrics),
	}
}

func (m *Monitor) isHealthyLocked() bool {
	for _, c := range m.components {
		if c.Status == StatusDown {
			return false
		}
	}
	return true
}