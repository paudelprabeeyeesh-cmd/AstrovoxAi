package monitor

import (
	"strings"
	"testing"
	"time"
)

func TestRegistryCounter(t *testing.T) {
	r := NewRegistry()
	r.Inc("requests", nil, 1)
	r.Inc("requests", nil, 1)
	m, ok := r.Get("requests", nil)
	if !ok {
		t.Fatal("expected metric")
	}
	if m.Value() != 2 {
		t.Errorf("expected 2, got %d", m.Value())
	}
}

func TestRegistryGauge(t *testing.T) {
	r := NewRegistry()
	r.Set("temp", nil, 42)
	m, _ := r.Get("temp", nil)
	if m.Value() != 42 || m.Type != Gauge {
		t.Errorf("expected gauge 42, got %d", m.Value())
	}
}

func TestRegistryHistogram(t *testing.T) {
	r := NewRegistry()
	r.Observe("latency", nil, 0.05)
	r.Observe("latency", nil, 5.0)
	m, ok := r.Get("latency", nil)
	if !ok {
		t.Fatal("expected histogram")
	}
	if m.hist.CountValue() != 2 {
		t.Errorf("expected 2 observations, got %d", m.hist.CountValue())
	}
}

func TestRegistryLabels(t *testing.T) {
	r := NewRegistry()
	r.Inc("calls", map[string]string{"op": "add"}, 3)
	r.Inc("calls", map[string]string{"op": "sub"}, 5)
	m1, _ := r.Get("calls", map[string]string{"op": "add"})
	m2, _ := r.Get("calls", map[string]string{"op": "sub"})
	if m1.Value() != 3 || m2.Value() != 5 {
		t.Error("labels should separate metrics")
	}
}

func TestRegistrySnapshot(t *testing.T) {
	r := NewRegistry()
	r.Inc("ops", nil, 1)
	s := r.Snapshot()
	if !strings.Contains(s, "counter") || !strings.Contains(s, "ops") {
		t.Errorf("unexpected snapshot: %s", s)
	}
}

func TestMetricTypeString(t *testing.T) {
	if Counter.String() != "counter" || Gauge.String() != "gauge" {
		t.Error("metric type strings")
	}
	if MetricHistogram.String() != "histogram" {
		t.Error("histogram string")
	}
}

func TestHistogramObserve(t *testing.T) {
	h := NewHistogram([]float64{1, 10})
	h.Observe(0.5)
	h.Observe(5)
	h.Observe(100)
	if h.CountValue() != 3 {
		t.Errorf("expected 3, got %d", h.CountValue())
	}
	if h.counts[0].Load() != 1 {
		t.Error("expected 1 in first bucket")
	}
}

func TestMonitorComponents(t *testing.T) {
	m := NewMonitor()
	m.RegisterComponent("db", "database")
	m.SetComponentStatus("db", StatusDown)
	h := m.Health()
	if h["db"] != StatusDown {
		t.Error("expected db down")
	}
	if m.IsHealthy() {
		t.Error("expected unhealthy")
	}
}

func TestMonitorAlerts(t *testing.T) {
	m := NewMonitor()
	m.Registry().Set("errs", nil, 10)
	m.AddRule(AlertRule{
		Name: "many-errors", Metric: "errs", Threshold: 5,
		Severity: "critical", Compare: "gt",
	})
	fired := m.Evaluate()
	if len(fired) != 1 {
		t.Fatalf("expected 1 alert, got %d", len(fired))
	}
	if !strings.Contains(fired[0].Message, "above") {
		t.Errorf("unexpected message %q", fired[0].Message)
	}
	// Rule should not fire again while still breached.
	if len(m.Evaluate()) != 0 {
		t.Error("rule should not re-fire")
	}
}

func TestMonitorAlertResets(t *testing.T) {
	m := NewMonitor()
	m.Registry().Set("errs", nil, 10)
	m.AddRule(AlertRule{Name: "r", Metric: "errs", Threshold: 5, Compare: "gt"})
	m.Evaluate()
	m.Registry().Set("errs", nil, 1)
	if len(m.Evaluate()) != 0 {
		t.Error("no fire when below threshold")
	}
	m.Registry().Set("errs", nil, 9)
	if len(m.Evaluate()) != 1 {
		t.Error("should fire again after recovery")
	}
}

func TestMonitorAlertLt(t *testing.T) {
	m := NewMonitor()
	m.Registry().Set("mem", nil, 1)
	m.AddRule(AlertRule{Name: "low", Metric: "mem", Threshold: 5, Compare: "lt"})
	if len(m.Evaluate()) != 1 {
		t.Error("expected lt alert to fire")
	}
}

func TestSeries(t *testing.T) {
	s := NewSeries("cpu", 3)
	for i := 1; i <= 6; i++ {
		s.Add(float64(i))
	}
	if len(s.Points) != 3 {
		t.Errorf("expected bounded 3 points, got %d", len(s.Points))
	}
	p, ok := s.Latest()
	if !ok || p.Value != 6 {
		t.Error("expected latest 6")
	}
	want := (4.0 + 5.0 + 6.0) / 3
	if s.Mean() < want-0.01 || s.Mean() > want+0.01 {
		t.Errorf("expected mean %f, got %f", want, s.Mean())
	}
}

func TestSeriesEmpty(t *testing.T) {
	s := NewSeries("x", 0)
	if _, ok := s.Latest(); ok {
		t.Error("expected no points")
	}
	if s.Mean() != 0 {
		t.Error("expected zero mean")
	}
}

func TestRenderDashboard(t *testing.T) {
	m := NewMonitor()
	m.RegisterComponent("api", "server")
	m.Registry().Inc("hits", nil, 7)
	html := m.RenderDashboard()
	if !strings.Contains(html, "<html>") || !strings.Contains(html, "api") {
		t.Error("expected HTML dashboard")
	}
	txt := m.RenderText()
	if !strings.Contains(txt, "Metrics") {
		t.Errorf("expected text metrics: %s", txt)
	}
}

func TestDashboardData(t *testing.T) {
	m := NewMonitor()
	m.RegisterComponent("c", "d")
	d := m.DashboardData()
	if d["healthy"] != true {
		t.Error("expected healthy")
	}
	if _, ok := d["uptime_seconds"]; !ok {
		t.Error("expected uptime")
	}
}

func TestTimestampInSeries(t *testing.T) {
	s := NewSeries("t", 5)
	s.Add(1)
	p, _ := s.Latest()
	if time.Since(p.Timestamp) > time.Minute {
		t.Error("expected recent timestamp")
	}
}