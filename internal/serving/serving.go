// Package serving provides a model serving runtime with request batching,
// quantization presets, and a simple metrics registry.
package serving

import (
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"
)

// Model is the interface for servable models.
type Model interface {
	Predict(batch [][]float32) ([][]float32, error)
	Name() string
	InputShape() []int
	OutputShape() []int
}

// Preprocessing is a preprocessing function for a model.
type Preprocessing func(input interface{}) ([]float32, error)

// Postprocessing is a postprocessing function for a model.
type Postprocessing func(output []float32) (interface{}, error)

// QuantizationType identifies a quantization scheme.
type QuantizationType int

const (
	QuantNone QuantizationType = iota
	QuantInt8
	QuantInt4
	QuantFP16
	QuantBF16
)

func (q QuantizationType) String() string {
	switch q {
	case QuantInt8:
		return "int8"
	case QuantInt4:
		return "int4"
	case QuantFP16:
		return "fp16"
	case QuantBF16:
		return "bf16"
	default:
		return "none"
	}
}

// MemorySavings returns the relative memory savings factor.
func (q QuantizationType) MemorySavings() float64 {
	switch q {
	case QuantInt8:
		return 0.25
	case QuantInt4:
		return 0.125
	case QuantFP16, QuantBF16:
		return 0.5
	default:
		return 1.0
	}
}

// ServingConfig holds serving configuration.
type ServingConfig struct {
	MaxBatchSize   int
	BatchTimeout   time.Duration
	MaxConcurrency int
	Quantization   QuantizationType
	ServePerf      bool
	WarmupRequests int
}

// DefaultServingConfig returns default config.
func DefaultServingConfig() *ServingConfig {
	return &ServingConfig{
		MaxBatchSize:   32,
		BatchTimeout:   10 * time.Millisecond,
		MaxConcurrency: 8,
		Quantization:   QuantNone,
		WarmupRequests: 3,
	}
}

// BatchRequest is a single inference request.
type BatchRequest struct {
	ID       string
	Input    interface{}
	Pre      Preprocessing
	Post     Postprocessing
	ResultCh chan interface{}
	ErrCh    chan error
	Enqueued time.Time
}

// RequestStats tracks serving metrics.
type RequestStats struct {
	TotalRequests  atomic.Int64
	Completed      atomic.Int64
	Failed         atomic.Int64
	TotalLatencyNs atomic.Int64
	BatchesFormed  atomic.Int64
	AvgBatchSize   atomic.Int64
}

// Server serves a model with dynamic batching.
type Server struct {
	config    *ServingConfig
	model     Model
	pre       Preprocessing
	post      Postprocessing
	queue     chan *BatchRequest
	stats     RequestStats
	wg        sync.WaitGroup
	running   atomic.Bool
	modelName string
}

// NewServer creates a model server.
func NewServer(model Model, config *ServingConfig) (*Server, error) {
	if model == nil {
		return nil, errors.New("model cannot be nil")
	}
	if config == nil {
		config = DefaultServingConfig()
	}
	return &Server{
		config:    config,
		model:     model,
		queue:     make(chan *BatchRequest, config.MaxBatchSize*4),
		modelName: model.Name(),
	}, nil
}

// SetPreprocessors sets global pre/post processing.
func (s *Server) SetPreprocessors(pre Preprocessing, post Postprocessing) {
	s.pre = pre
	s.post = post
}

// Start starts the batching loop.
func (s *Server) Start() {
	if s.running.Swap(true) {
		return
	}
	workers := s.config.MaxConcurrency
	if workers < 1 {
		workers = 1
	}
	s.wg.Add(workers)
	for i := 0; i < workers; i++ {
		go s.batchLoop()
	}
}

// Stop stops the server.
func (s *Server) Stop() {
	if !s.running.Swap(false) {
		return
	}
	close(s.queue)
	s.wg.Wait()
}

func (s *Server) batchLoop() {
	defer s.wg.Done()
	for req := range s.queue {
		if req == nil {
			continue
		}
		s.stats.TotalRequests.Add(1)
		start := time.Now()

		// Collect a batch, bounded by size and by the batch timeout.
		batch := []*BatchRequest{req}
		maxBatch := s.config.MaxBatchSize
		if maxBatch <= 0 {
			maxBatch = 1
		}
		deadline := time.NewTimer(s.config.BatchTimeout)
	collect:
		for len(batch) < maxBatch {
			select {
			case next := <-s.queue:
				if next != nil {
					batch = append(batch, next)
				}
			case <-deadline.C:
				break collect
			}
		}
		deadline.Stop()

		s.stats.BatchesFormed.Add(1)
		s.stats.AvgBatchSize.Add(int64(len(batch)))

		// Preprocess
		inputs := make([][]float32, 0, len(batch))
		for _, r := range batch {
			pre := r.Pre
			if pre == nil {
				pre = s.pre
			}
			var in []float32
			var err error
			if pre != nil {
				in, err = pre(r.Input)
			} else if f, ok := r.Input.([]float32); ok {
				in = f
			} else {
				err = fmt.Errorf("no preprocessor for input type %T", r.Input)
			}
			if err != nil {
				s.stats.Failed.Add(1)
				r.ErrCh <- err
				continue
			}
			inputs = append(inputs, in)
		}

		// Predict
		outputs, err := s.model.Predict(inputs)
		if err != nil {
			s.stats.Failed.Add(1)
			for _, r := range batch {
				r.ErrCh <- err
			}
			continue
		}

		// Postprocess and reply
		for i, r := range batch {
			if i >= len(outputs) {
				continue
			}
			post := r.Post
			if post == nil {
				post = s.post
			}
			var result interface{} = outputs[i]
			if post != nil {
				result, err = post(outputs[i])
				if err != nil {
					s.stats.Failed.Add(1)
					r.ErrCh <- err
					continue
				}
			}
			s.stats.Completed.Add(1)
			r.ResultCh <- result
		}
		s.stats.TotalLatencyNs.Add(time.Since(start).Nanoseconds())
	}
}

// Predict submits a request and waits for the result.
func (s *Server) Predict(input interface{}, timeout time.Duration) (interface{}, error) {
	if !s.running.Load() {
		return nil, errors.New("server not started")
	}
	req := &BatchRequest{
		ID:       fmt.Sprintf("req-%d", time.Now().UnixNano()),
		Input:    input,
		ResultCh: make(chan interface{}, 1),
		ErrCh:    make(chan error, 1),
		Enqueued: time.Now(),
	}
	select {
	case s.queue <- req:
	case <-time.After(timeout):
		return nil, errors.New("request queue full")
	}
	select {
	case res := <-req.ResultCh:
		return res, nil
	case err := <-req.ErrCh:
		return nil, err
	case <-time.After(timeout):
		return nil, errors.New("prediction timed out")
	}
}

// PredictAsync submits a request without waiting.
func (s *Server) PredictAsync(input interface{}, pre Preprocessing, post Postprocessing) (<-chan interface{}, <-chan error, error) {
	if !s.running.Load() {
		return nil, nil, errors.New("server not started")
	}
	req := &BatchRequest{
		ID:       fmt.Sprintf("req-%d", time.Now().UnixNano()),
		Input:    input,
		Pre:      pre,
		Post:     post,
		ResultCh: make(chan interface{}, 1),
		ErrCh:    make(chan error, 1),
		Enqueued: time.Now(),
	}
	select {
	case s.queue <- req:
		return req.ResultCh, req.ErrCh, nil
	default:
		return nil, nil, errors.New("request queue full")
	}
}

// Stats returns a snapshot of the request statistics.
func (s *Server) Stats() ServingMetrics {
	total := s.stats.TotalRequests.Load()
	completed := s.stats.Completed.Load()
	batches := s.stats.BatchesFormed.Load()
	avgLatency := int64(0)
	if completed > 0 {
		avgLatency = s.stats.TotalLatencyNs.Load() / completed
	}
	avgBatch := float64(0)
	if batches > 0 {
		avgBatch = float64(s.stats.AvgBatchSize.Load()) / float64(batches)
	}
	return ServingMetrics{
		TotalRequests: total,
		Completed:     completed,
		Failed:        s.stats.Failed.Load(),
		BatchesFormed: batches,
		AvgBatchSize:  avgBatch,
		AvgLatencyMs:  float64(avgLatency) / 1e6,
	}
}

// ServingMetrics is a snapshot of server metrics.
type ServingMetrics struct {
	TotalRequests int64
	Completed     int64
	Failed        int64
	BatchesFormed int64
	AvgBatchSize  float64
	AvgLatencyMs  float64
}

// DummyModel is a simple model for testing.
type DummyModel struct {
	name    string
	inShape []int
}

// NewDummyModel creates a dummy model.
func NewDummyModel(name string, inDim, outDim int) *DummyModel {
	return &DummyModel{name: name, inShape: []int{inDim, outDim}}
}

// Name returns the model name.
func (d *DummyModel) Name() string { return d.name }

// InputShape returns the input shape.
func (d *DummyModel) InputShape() []int { return d.inShape }

// OutputShape returns the output shape.
func (d *DummyModel) OutputShape() []int { return d.inShape }

// Predict applies a simple linear transform.
func (d *DummyModel) Predict(batch [][]float32) ([][]float32, error) {
	outDim := d.inShape[1]
	out := make([][]float32, len(batch))
	for i, in := range batch {
		o := make([]float32, outDim)
		if len(in) > 0 {
			for j := 0; j < outDim; j++ {
				o[j] = in[j%len(in)] * 0.5
			}
		}
		out[i] = o
	}
	return out, nil
}

// Quantizer converts float weights to lower precision.
type Quantizer struct {
	scheme QuantizationType
}

// NewQuantizer creates a quantizer.
func NewQuantizer(s QuantizationType) *Quantizer {
	return &Quantizer{scheme: s}
}

// Scheme returns the quantization scheme.
func (q *Quantizer) Scheme() QuantizationType { return q.scheme }

// EstimateMemory estimates model memory in bytes.
func (q *Quantizer) EstimateMemory(params int64, elementSize int) int64 {
	return int64(float64(params*int64(elementSize)) * q.scheme.MemorySavings())
}
