package inference_test

import (
	"context"
	"testing"
	"time"

	"github.com/astrovox/astrovox/inference"
	"github.com/astrovox/astrovox/model"
	"github.com/astrovox/astrovox/tensor"
)

// BenchmarkExecutorThroughput measures end-to-end request throughput
// through the scheduler: submission, queueing, model execution, and
// result delivery. The model is a real MLP forward pass.
func BenchmarkExecutorThroughput(b *testing.B) {
	m, err := model.NewMLP("mlp", []int{8, 16, 4}, model.ActRelu, 5)
	if err != nil {
		b.Fatal(err)
	}
	exec, err := inference.NewExecutor(&inference.ModuleExecutable{Module: m}, 4, inference.DefaultLimits)
	if err != nil {
		b.Fatal(err)
	}
	defer exec.Shutdown(5 * time.Second)
	in, err := tensor.Zeros(tensor.Float64, []int{1, 8})
	if err != nil {
		b.Fatal(err)
	}
	inputs := map[string]*tensor.Tensor{inference.InputKey: in}
	ctx := context.Background()
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		res, err := exec.Run(ctx, inference.Request{ID: "bench", Inputs: inputs})
		if err != nil {
			b.Fatal(err)
		}
		if len(res.Outputs) == 0 {
			b.Fatal("no outputs")
		}
	}
}

// BenchmarkExecutorQueueLatency submits many concurrent requests and
// reports total wall time for the batch, which approximates queue wait
// plus execution under contention.
func BenchmarkExecutorQueueLatency(b *testing.B) {
	m, err := model.NewMLP("mlp", []int{8, 16, 4}, model.ActRelu, 5)
	if err != nil {
		b.Fatal(err)
	}
	exec, err := inference.NewExecutor(&inference.ModuleExecutable{Module: m}, 2, inference.DefaultLimits)
	if err != nil {
		b.Fatal(err)
	}
	defer exec.Shutdown(5 * time.Second)
	in, err := tensor.Zeros(tensor.Float64, []int{1, 8})
	if err != nil {
		b.Fatal(err)
	}
	inputs := map[string]*tensor.Tensor{inference.InputKey: in}
	ctx := context.Background()
	// The batch must fit the bounded queue (4 workers x 4 slots + in
	// flight); a larger batch measures backpressure, not latency.
	const batch = 4
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		var done int
		errs := make(chan error, batch)
		for j := 0; j < batch; j++ {
			go func() {
				res, err := exec.Run(ctx, inference.Request{ID: "bench", Inputs: inputs})
				if err == nil && len(res.Outputs) == 0 {
					errs <- errNoOutputs
					return
				}
				errs <- err
			}()
		}
		for j := 0; j < batch; j++ {
			if err := <-errs; err != nil {
				b.Fatal(err)
			}
			done++
		}
		if done != batch {
			b.Fatalf("completed %d, want %d", done, batch)
		}
	}
}

var errNoOutputs = &noOutputs{}

type noOutputs struct{}

func (*noOutputs) Error() string { return "no outputs" }
