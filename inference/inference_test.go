package inference_test

import (
	"context"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/astrovox/astrovox/inference"
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/model"
	"github.com/astrovox/astrovox/tensor"
)

// fakeModel is a deterministic Executable: it returns the input scaled
// by a constant, so outputs are checkable without a real model.
type fakeModel struct {
	scale     float64
	delay     time.Duration
	calls     atomic.Int64
	failEvery int64 // if > 0, the Nth call fails
}

func (f *fakeModel) Forward(ctx context.Context, inputs map[string]*tensor.Tensor) (map[string]*tensor.Tensor, error) {
	n := f.calls.Add(1)
	if f.failEvery > 0 && n%f.failEvery == 0 {
		return nil, errors.New(errors.CodeInternal, "injected failure")
	}
	if f.delay > 0 {
		select {
		case <-time.After(f.delay):
		case <-ctx.Done():
			return nil, errors.Wrap(ctx.Err(), errors.CodeCancelled, "fake model interrupted")
		}
	}
	x := inputs[inference.InputKey]
	out, err := tensor.Zeros(tensor.Float64, x.Shape().Dims())
	if err != nil {
		return nil, err
	}
	for i, v := range x.Float64() {
		out.Float64()[i] = v * f.scale
	}
	return map[string]*tensor.Tensor{inference.OutputKey: out}, nil
}

func inputTensor(vals ...float64) *tensor.Tensor {
	t, err := tensor.Zeros(tensor.Float64, []int{len(vals)})
	if err != nil {
		panic(err)
	}
	copy(t.Float64(), vals)
	return t
}

func newExecutor(t *testing.T, m inference.Executable, workers int) *inference.Executor {
	t.Helper()
	e, err := inference.NewExecutor(m, workers, inference.DefaultLimits)
	if err != nil {
		t.Fatalf("NewExecutor: %v", err)
	}
	t.Cleanup(func() { _ = e.Shutdown(2 * time.Second) })
	return e
}

func TestRunSingleRequest(t *testing.T) {
	e := newExecutor(t, &fakeModel{scale: 2}, 2)
	res, err := e.Run(context.Background(), inference.Request{
		ID:     "r1",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(1, 2, 3)},
	})
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	out := res.Outputs[inference.OutputKey]
	if out == nil {
		t.Fatal("no output tensor")
	}
	for i, want := range []float64{2, 4, 6} {
		if got := out.Float64()[i]; got != want {
			t.Fatalf("output[%d] = %v, want %v", i, got, want)
		}
	}
	if res.Exec < 0 || res.Wait < 0 {
		t.Fatalf("durations must be non-negative: wait=%v exec=%v", res.Wait, res.Exec)
	}
	s := e.Stats()
	if s.Completed != 1 || s.Failed != 0 || s.Rejected != 0 {
		t.Fatalf("stats = %+v", s)
	}
}

func TestValidationRejectsMalformedRequests(t *testing.T) {
	e := newExecutor(t, &fakeModel{scale: 1}, 1)
	// Empty ID.
	if _, err := e.Submit(context.Background(), inference.Request{Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(1)}}); !errors.IsCode(err, errors.CodeInvalidArgument) {
		t.Fatalf("empty ID: %v", err)
	}
	// No inputs.
	if _, err := e.Submit(context.Background(), inference.Request{ID: "x"}); !errors.IsCode(err, errors.CodeInvalidArgument) {
		t.Fatalf("no inputs: %v", err)
	}
	// Expired deadline.
	past := time.Now().Add(-time.Second)
	if _, err := e.Submit(context.Background(), inference.Request{
		ID:       "x",
		Inputs:   map[string]*tensor.Tensor{inference.InputKey: inputTensor(1)},
		Deadline: past,
	}); !errors.IsCode(err, errors.CodeTimeout) {
		t.Fatalf("expired deadline: %v", err)
	}
	// Element limit.
	small, err := inference.NewExecutor(&fakeModel{}, 1, inference.Limits{MaxInputs: 1, MaxElements: 2, MaxOutputElements: 2})
	if err != nil {
		t.Fatal(err)
	}
	defer small.Shutdown(time.Second)
	if _, err := small.Submit(context.Background(), inference.Request{
		ID:     "x",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(1, 2, 3)},
	}); !errors.IsCode(err, errors.CodeResourceExhausted) {
		t.Fatalf("element limit: %v", err)
	}
	s := e.Stats()
	if s.Rejected != 3 {
		t.Fatalf("rejected = %d, want 3", s.Rejected)
	}
}

func TestNilModelIsRefused(t *testing.T) {
	if _, err := inference.NewExecutor(nil, 1, inference.DefaultLimits); !errors.IsCode(err, errors.CodeInvalidArgument) {
		t.Fatalf("nil model: %v", err)
	}
}

func TestConcurrentRequestsComplete(t *testing.T) {
	e := newExecutor(t, &fakeModel{scale: 3}, 4)
	const n = 50
	var wg sync.WaitGroup
	errs := make(chan error, n)
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			// The bounded queue refuses overflow: retry on
			// CodeQueueFull, which is backpressure, not failure.
			var res inference.Result
			var err error
			for attempt := 0; attempt < 1000; attempt++ {
				res, err = e.Run(context.Background(), inference.Request{
					ID:     "c",
					Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(float64(i))},
				})
				if err == nil || !errors.IsCode(err, errors.CodeQueueFull) {
					break
				}
				time.Sleep(time.Millisecond)
			}
			if err != nil {
				errs <- err
				return
			}
			if got := res.Outputs[inference.OutputKey].Float64()[0]; got != float64(i)*3 {
				errs <- errors.New(errors.CodeInternal, "wrong output")
			}
		}(i)
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Fatalf("concurrent request failed: %v", err)
	}
	s := e.Stats()
	if s.Completed != n {
		t.Fatalf("completed = %d, want %d", s.Completed, n)
	}
	if s.InFlight != 0 {
		t.Fatalf("in flight = %d, want 0", s.InFlight)
	}
}

func TestDeadlineExpiresDuringExecution(t *testing.T) {
	// The model sleeps longer than the deadline allows.
	e := newExecutor(t, &fakeModel{scale: 1, delay: 200 * time.Millisecond}, 1)
	res, err := e.Run(context.Background(), inference.Request{
		ID:       "slow",
		Inputs:   map[string]*tensor.Tensor{inference.InputKey: inputTensor(1)},
		Deadline: time.Now().Add(20 * time.Millisecond),
	})
	if !errors.IsCode(err, errors.CodeTimeout) {
		t.Fatalf("err = %v, want a timeout", err)
	}
	if res.Outputs != nil {
		t.Fatal("a timed-out request produced outputs")
	}
	if s := e.Stats(); s.TimedOut == 0 {
		t.Fatalf("timed-out counter not incremented: %+v", s)
	}
}

func TestContextCancellation(t *testing.T) {
	e := newExecutor(t, &fakeModel{scale: 1, delay: 200 * time.Millisecond}, 1)
	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		time.Sleep(20 * time.Millisecond)
		cancel()
	}()
	_, err := e.Run(ctx, inference.Request{
		ID:     "c",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(1)},
	})
	if !errors.IsCode(err, errors.CodeCancelled) {
		t.Fatalf("err = %v, want a cancellation", err)
	}
	// A cancelled submission before enqueue is also refused, not run.
	dead, cancel2 := context.WithCancel(context.Background())
	cancel2()
	if _, err := e.Submit(dead, inference.Request{
		ID:     "d",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(1)},
	}); !errors.IsCode(err, errors.CodeCancelled) {
		t.Fatalf("cancelled submit: %v", err)
	}
}

func TestBackpressureIsExplicit(t *testing.T) {
	// One worker, slow model: the bounded queue fills and later
	// submissions are refused with CodeQueueFull instead of blocking.
	e := newExecutor(t, &fakeModel{scale: 1, delay: 50 * time.Millisecond}, 1)
	first, err := e.Submit(context.Background(), inference.Request{
		ID:     "q0",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(1)},
	})
	if err != nil {
		t.Fatalf("first submit: %v", err)
	}
	var refused bool
	for i := 1; i < 100; i++ {
		if _, err := e.Submit(context.Background(), inference.Request{
			ID:     "q",
			Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(1)},
		}); err != nil {
			if !errors.IsCode(err, errors.CodeQueueFull) {
				t.Fatalf("submit %d: %v, want queue-full", i, err)
			}
			refused = true
			break
		}
	}
	if !refused {
		t.Fatal("the bounded queue never refused work: backpressure is not explicit")
	}
	if res := first.Wait(); res.Err != nil {
		t.Fatalf("accepted request failed while the queue was full: %v", res.Err)
	}
}

func TestModelFailureSurfaces(t *testing.T) {
	e := newExecutor(t, &fakeModel{scale: 1, failEvery: 1}, 1)
	res, err := e.Run(context.Background(), inference.Request{
		ID:     "f",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(1)},
	})
	if !errors.IsCode(err, errors.CodeInternal) {
		t.Fatalf("err = %v, want the injected failure", err)
	}
	if res.Outputs != nil {
		t.Fatal("a failed request produced outputs")
	}
	if s := e.Stats(); s.Failed != 1 {
		t.Fatalf("failed = %d, want 1", s.Failed)
	}
}

func TestShutdownRefusesNewWork(t *testing.T) {
	e := newExecutor(t, &fakeModel{scale: 1}, 1)
	if err := e.Shutdown(2 * time.Second); err != nil {
		t.Fatalf("Shutdown: %v", err)
	}
	if _, err := e.Submit(context.Background(), inference.Request{
		ID:     "s",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: inputTensor(1)},
	}); !errors.IsCode(err, errors.CodeCancelled) {
		t.Fatalf("submit after shutdown: %v", err)
	}
	// Idempotent.
	if err := e.Shutdown(time.Second); err != nil {
		t.Fatalf("second Shutdown: %v", err)
	}
}

// TestEndToEndThroughModule wires a real model through the executor:
// the model's forward pass runs on the actual kernels, not a fake.
func TestEndToEndThroughModule(t *testing.T) {
	m, err := model.NewMLP("mlp", []int{3, 5, 2}, model.ActRelu, 42)
	if err != nil {
		t.Fatalf("NewMLP: %v", err)
	}
	e := newExecutor(t, &inference.ModuleExecutable{Module: m}, 2)

	batch := 4
	in, err := tensor.Zeros(tensor.Float64, []int{batch, 3})
	if err != nil {
		t.Fatalf("Zeros: %v", err)
	}
	for i := range in.Float64() {
		in.Float64()[i] = float64(i%5) - 2
	}
	res, err := e.Run(context.Background(), inference.Request{
		ID:     "mlp",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: in},
	})
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	out := res.Outputs[inference.OutputKey]
	if out == nil {
		t.Fatal("no output")
	}
	shape := out.Shape().Dims()
	if shape[0] != batch || shape[1] != 2 {
		t.Fatalf("output shape = %v, want [%d 2]", shape, batch)
	}
	// Hidden relu: the output layer is linear, so negatives are allowed,
	// but outputs must be finite.
	for _, v := range out.Float64() {
		if v != v || v > 1e308 || v < -1e308 {
			t.Fatalf("non-finite output %v", v)
		}
	}
}
