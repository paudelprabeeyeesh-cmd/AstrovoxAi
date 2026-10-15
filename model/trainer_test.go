package model

import (
	"math"
	"testing"

	"github.com/astrovox/astrovox/tensor"
)

func scheduleData(t *testing.T) *Dataset {
	t.Helper()
	// y = 2x - 0.5, five deterministic points.
	in, err := tensor.Zeros(tensor.Float64, []int{5, 1})
	if err != nil {
		t.Fatal(err)
	}
	tg, err := tensor.Zeros(tensor.Float64, []int{5, 1})
	if err != nil {
		t.Fatal(err)
	}
	for i, x := range []float64{-1, -0.5, 0, 0.5, 1} {
		in.Float64()[i] = x
		tg.Float64()[i] = 2*x - 0.5
	}
	ds, err := NewDataset(in, tg)
	if err != nil {
		t.Fatal(err)
	}
	return ds
}

func TestScheduleValues(t *testing.T) {
	c := ConstantSchedule{Base: 0.1}
	for _, s := range []int{0, 1, 100} {
		if c.LR(s) != 0.1 {
			t.Fatalf("constant at %d = %v", s, c.LR(s))
		}
	}
	s := StepSchedule{Base: 0.1, StepSize: 10, Gamma: 0.5}
	// Steps 0,10,20,30,40 -> 0.1, 0.05, 0.025, 0.0125, 0.00625.
	want := []float64{0.1, 0.05, 0.025, 0.0125, 0.00625}
	for i, w := range want {
		step := i * 10
		if got := s.LR(step); math.Abs(got-w) > 1e-15 {
			t.Fatalf("step schedule at %d = %v, want %v", step, got, w)
		}
	}
	cos := CosineSchedule{Base: 0.1, Min: 0.01, Total: 10}
	if got := cos.LR(0); math.Abs(got-0.1) > 1e-15 {
		t.Fatalf("cosine at 0 = %v, want 0.1", got)
	}
	if got := cos.LR(5); math.Abs(got-(0.01+0.09/2)) > 1e-15 {
		t.Fatalf("cosine at 5 = %v, want 0.055", got)
	}
	if got := cos.LR(10); got != 0.01 {
		t.Fatalf("cosine past total = %v, want min 0.01", got)
	}
	// Validation rejects bad schedules.
	if err := validateSchedule(ConstantSchedule{Base: 0}); err == nil {
		t.Fatal("non-positive constant accepted")
	}
	if err := validateSchedule(StepSchedule{StepSize: 0}); err == nil {
		t.Fatal("zero step size accepted")
	}
	if err := validateSchedule(CosineSchedule{Base: 1, Min: 2, Total: 5}); err == nil {
		t.Fatal("min above base accepted")
	}
	if err := validateSchedule(nil); err == nil {
		t.Fatal("nil schedule accepted")
	}
}

func TestTrainConfigValidation(t *testing.T) {
	base := func() TrainConfig {
		return TrainConfig{Steps: 2, BatchSize: 2, LRSchedule: ConstantSchedule{Base: 0.1}}
	}
	if err := base().Validate(); err != nil {
		t.Fatalf("valid config rejected: %v", err)
	}
	c := base()
	c.Steps = 0
	if err := c.Validate(); err == nil {
		t.Fatal("zero steps accepted")
	}
	c = base()
	c.LRSchedule = nil
	if err := c.Validate(); err == nil {
		t.Fatal("nil schedule accepted")
	}
}

// TestTrainerReproducible: same seed and config produce identical
// parameters, which is what makes resumed runs meaningful.
func TestTrainerReproducible(t *testing.T) {
	ds := scheduleData(t)
	run := func() []float64 {
		m, err := NewMLP("mlp", []int{1, 4, 1}, ActRelu, 123)
		if err != nil {
			t.Fatal(err)
		}
		tr, err := NewTrainer(m, TrainConfig{
			Seed: 7, Steps: 30, BatchSize: 5,
			Optimizer: OptimizerSGD, LRSchedule: ConstantSchedule{Base: 0.05},
		})
		if err != nil {
			t.Fatal(err)
		}
		res, err := tr.Train(ds)
		if err != nil {
			t.Fatal(err)
		}
		if res.Metrics[0].Loss <= res.FinalLoss {
			t.Fatalf("loss did not decrease: %v -> %v", res.Metrics[0].Loss, res.FinalLoss)
		}
		out := make([]float64, 0)
		for _, p := range m.Parameters() {
			out = append(out, p.Value.Float64()...)
		}
		return out
	}
	a := run()
	b := run()
	if len(a) != len(b) {
		t.Fatal("parameter counts differ")
	}
	for i := range a {
		if a[i] != b[i] {
			t.Fatalf("parameter %d differs between identical runs: %v vs %v", i, a[i], b[i])
		}
	}
}

// TestTrainerResumeEqualsUninterrupted: resuming from a checkpoint must
// continue the trajectory, not restart it. The optimizer state (step
// counter) must survive the round trip.
func TestTrainerResumeEqualsUninterrupted(t *testing.T) {
	ds := scheduleData(t)

	// Uninterrupted run.
	full, err := NewMLP("mlp", []int{1, 4, 1}, ActRelu, 99)
	if err != nil {
		t.Fatal(err)
	}
	fullTrainer, err := NewTrainer(full, TrainConfig{
		Seed: 1, Steps: 40, BatchSize: 5,
		Optimizer: OptimizerSGD, LRSchedule: ConstantSchedule{Base: 0.05},
	})
	if err != nil {
		t.Fatal(err)
	}
	res1, err := fullTrainer.Train(ds)
	if err != nil {
		t.Fatal(err)
	}

	// Interrupted: 20 steps, checkpoint, restore, 20 more steps.
	part, err := NewMLP("mlp", []int{1, 4, 1}, ActRelu, 99)
	if err != nil {
		t.Fatal(err)
	}
	cfg := TrainConfig{
		Seed: 1, Steps: 20, BatchSize: 5,
		Optimizer: OptimizerSGD, LRSchedule: ConstantSchedule{Base: 0.05},
	}
	partTrainer, err := NewTrainer(part, cfg)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := partTrainer.Train(ds); err != nil {
		t.Fatal(err)
	}
	cp, err := partTrainer.Checkpoint()
	if err != nil {
		t.Fatal(err)
	}
	if cp.Optimizer == nil || cp.Optimizer.Step != 20 {
		t.Fatalf("checkpoint step = %+v, want 20", cp.Optimizer)
	}

	resume, err := NewMLP("mlp", []int{1, 4, 1}, ActRelu, 12345) // different init
	if err != nil {
		t.Fatal(err)
	}
	resumeTrainer, err := NewTrainer(resume, TrainConfig{
		Seed: 1, Steps: 20, BatchSize: 5,
		Optimizer: OptimizerSGD, LRSchedule: ConstantSchedule{Base: 0.05},
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := resumeTrainer.Restore(cp); err != nil {
		t.Fatal(err)
	}
	if resumeTrainer.StepCount() != 20 {
		t.Fatalf("restored step count = %d, want 20", resumeTrainer.StepCount())
	}
	res2, err := resumeTrainer.Train(ds)
	if err != nil {
		t.Fatal(err)
	}

	// The resumed run's final loss must match the uninterrupted run's
	// (same seed, same data, same schedule through step 40).
	if math.Abs(res1.FinalLoss-res2.FinalLoss) > 1e-9 {
		t.Fatalf("resumed final loss %v != uninterrupted %v", res2.FinalLoss, res1.FinalLoss)
	}
	// Parameters must match bit-for-bit.
	pa := full.Parameters()
	pb := resume.Parameters()
	for i := range pa {
		va, vb := pa[i].Value.Float64(), pb[i].Value.Float64()
		for j := range va {
			if va[j] != vb[j] {
				t.Fatalf("parameter %d[%d]: resumed %v != uninterrupted %v", i, j, vb[j], va[j])
			}
		}
	}
}

// TestTrainerRejectsMismatchedOptimizer: restoring Adam state into an
// SGD trainer must fail loudly rather than silently changing the rule.
func TestTrainerRejectsMismatchedOptimizer(t *testing.T) {
	m, err := NewMLP("mlp", []int{1, 2, 1}, ActRelu, 1)
	if err != nil {
		t.Fatal(err)
	}
	tr, err := NewTrainer(m, TrainConfig{
		Steps: 1, BatchSize: 1, LRSchedule: ConstantSchedule{Base: 0.1},
		Optimizer: OptimizerAdam,
	})
	if err != nil {
		t.Fatal(err)
	}
	cp, err := tr.Checkpoint()
	if err != nil {
		t.Fatal(err)
	}
	cp.Optimizer.Kind = "sgd"
	if err := tr.Restore(cp); err == nil {
		t.Fatal("a mismatched optimizer checkpoint was accepted")
	}
}

func TestDatasetBatching(t *testing.T) {
	ds := scheduleData(t)
	if ds.Len() != 5 {
		t.Fatalf("len = %d, want 5", ds.Len())
	}
	if n := ds.BatchCount(2); n != 3 {
		t.Fatalf("batch count = %d, want 3", n)
	}
	in, tg, err := ds.Batch(2, 2) // last partial batch: 2 elements here
	if err != nil {
		t.Fatal(err)
	}
	if in.Shape().Dim(0) != 2 || tg.Shape().Dim(0) != 2 {
		t.Fatalf("batch shapes = %v %v", in.Shape().Dims(), tg.Shape().Dims())
	}
	if _, _, err := ds.Batch(5, 2); err == nil {
		t.Fatal("out-of-range batch accepted")
	}
	if err := (TrainConfig{Steps: 1, BatchSize: 1, LRSchedule: ConstantSchedule{Base: 0.1}}).Validate(); err != nil {
		t.Fatalf("valid config rejected: %v", err)
	}
}

func TestTrainerClippingConfig(t *testing.T) {
	ds := scheduleData(t)
	m, err := NewMLP("mlp", []int{1, 3, 1}, ActRelu, 3)
	if err != nil {
		t.Fatal(err)
	}
	tr, err := NewTrainer(m, TrainConfig{
		Steps: 10, BatchSize: 5, LRSchedule: ConstantSchedule{Base: 0.05},
		ClipGradNorm: 1.0,
	})
	if err != nil {
		t.Fatal(err)
	}
	res, err := tr.Train(ds)
	if err != nil {
		t.Fatal(err)
	}
	// With clipping at 1, recorded norms may exceed 1 (pre-clip) but the
	// run must still converge.
	if res.FinalLoss >= res.Metrics[0].Loss {
		t.Fatalf("clipped training did not reduce loss: %v", res.Metrics[0].Loss)
	}
	for _, m := range res.Metrics {
		if math.IsNaN(m.Loss) {
			t.Fatal("NaN loss recorded")
		}
	}
}

// TestTrainerStepBackedByRealGradients guards against a trainer that
// "converges" without differentiating: the recorded gradient norm must
// be positive for a model that has not yet fit the data.
func TestTrainerStepBackedByRealGradients(t *testing.T) {
	ds := scheduleData(t)
	m, err := NewMLP("mlp", []int{1, 3, 1}, ActRelu, 5)
	if err != nil {
		t.Fatal(err)
	}
	tr, err := NewTrainer(m, TrainConfig{Steps: 2, BatchSize: 5, LRSchedule: ConstantSchedule{Base: 0.05}})
	if err != nil {
		t.Fatal(err)
	}
	res, err := tr.Train(ds)
	if err != nil {
		t.Fatal(err)
	}
	if res.Metrics[0].GradNorm <= 0 {
		t.Fatal("first step recorded a zero gradient norm: the loss is not connected to the parameters")
	}
}
