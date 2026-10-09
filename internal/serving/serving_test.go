package serving

import (
	"testing"
	"time"
)

func TestQuantizationType(t *testing.T) {
	if QuantInt8.String() != "int8" || QuantInt4.String() != "int4" {
		t.Error("quant strings")
	}
	if QuantNone.String() != "none" || QuantFP16.String() != "fp16" {
		t.Error("quant strings 2")
	}
	if QuantBF16.String() != "bf16" {
		t.Error("bf16")
	}
	if QuantNone.MemorySavings() != 1.0 {
		t.Error("none savings should be 1")
	}
	if QuantInt4.MemorySavings() != 0.125 {
		t.Errorf("int4 savings, got %f", QuantInt4.MemorySavings())
	}
}

func TestNewServer(t *testing.T) {
	s, err := NewServer(NewDummyModel("m", 4, 2), DefaultServingConfig())
	if err != nil {
		t.Fatal(err)
	}
	if s.modelName != "m" {
		t.Errorf("got %s", s.modelName)
	}
}

func TestNewServerNilModel(t *testing.T) {
	if _, err := NewServer(nil, nil); err == nil {
		t.Error("expected error")
	}
}

func TestServerPredict(t *testing.T) {
	s, _ := NewServer(NewDummyModel("m", 4, 2), &ServingConfig{
		MaxBatchSize: 4, BatchTimeout: 5 * time.Millisecond,
	})
	s.Start()
	defer s.Stop()

	in := []float32{1, 2, 3, 4}
	out, err := s.Predict(in, 2*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	vec, ok := out.([]float32)
	if !ok {
		t.Fatalf("expected []float32, got %T", out)
	}
	if len(vec) != 2 {
		t.Errorf("expected 2 outputs, got %d", len(vec))
	}
}

func TestServerPredictNotStarted(t *testing.T) {
	s, _ := NewServer(NewDummyModel("m", 4, 2), DefaultServingConfig())
	if _, err := s.Predict([]float32{1, 2, 3, 4}, time.Second); err == nil {
		t.Error("expected not started error")
	}
}

func TestServerPredictAsync(t *testing.T) {
	s, _ := NewServer(NewDummyModel("m", 4, 2), &ServingConfig{
		MaxBatchSize: 4, BatchTimeout: 5 * time.Millisecond,
	})
	s.Start()
	defer s.Stop()
	res, errs, err := s.PredictAsync([]float32{1, 2, 3, 4}, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	select {
	case <-res:
	case e := <-errs:
		t.Fatal(e)
	case <-time.After(2 * time.Second):
		t.Fatal("timeout")
	}
}

func TestServerConcurrent(t *testing.T) {
	s, _ := NewServer(NewDummyModel("m", 4, 2), &ServingConfig{
		MaxBatchSize: 8, BatchTimeout: 5 * time.Millisecond, MaxConcurrency: 4,
	})
	s.Start()
	defer s.Stop()

	done := make(chan error, 10)
	for i := 0; i < 10; i++ {
		go func() {
			_, err := s.Predict([]float32{1, 2, 3, 4}, 3*time.Second)
			done <- err
		}()
	}
	for i := 0; i < 10; i++ {
		if err := <-done; err != nil {
			t.Fatal(err)
		}
	}
	st := s.Stats()
	if st.Completed != 10 {
		t.Errorf("expected 10 completed, got %d", st.Completed)
	}
	if st.AvgBatchSize < 1 {
		t.Error("expected batches to form")
	}
}

func TestDummyModel(t *testing.T) {
	m := NewDummyModel("d", 2, 4)
	out, err := m.Predict([][]float32{{1, 2}})
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 || len(out[0]) != 4 {
		t.Errorf("got %d x %d", len(out), len(out[0]))
	}
	if m.Name() != "d" {
		t.Error("name")
	}
	if len(m.InputShape()) != 2 {
		t.Error("shape")
	}
}

func TestServerCustomPrePost(t *testing.T) {
	s, _ := NewServer(NewDummyModel("m", 2, 2), &ServingConfig{
		MaxBatchSize: 2, BatchTimeout: 5 * time.Millisecond,
	})
	s.SetPreprocessors(
		func(in interface{}) ([]float32, error) { return in.([]float32), nil },
		func(out []float32) (interface{}, error) { return float64(out[0]), nil },
	)
	s.Start()
	defer s.Stop()
	res, err := s.Predict([]float32{4, 4}, 2*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := res.(float64); !ok {
		t.Errorf("expected float64, got %T", res)
	}
}

func TestQuantizer(t *testing.T) {
	q := NewQuantizer(QuantInt8)
	if q.Scheme() != QuantInt8 {
		t.Error("scheme")
	}
	// 1M params * 4 bytes = 4MB, int8 -> 1MB
	if got := q.EstimateMemory(1000000, 4); got != 1000000 {
		t.Errorf("expected 1000000, got %d", got)
	}
}

func TestDefaultServingConfig(t *testing.T) {
	c := DefaultServingConfig()
	if c.MaxBatchSize != 32 {
		t.Errorf("expected batch 32, got %d", c.MaxBatchSize)
	}
	if c.MaxConcurrency != 8 {
		t.Errorf("expected concurrency 8, got %d", c.MaxConcurrency)
	}
}