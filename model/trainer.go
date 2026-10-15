package model

import (
	"fmt"

	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/internal/checkpoint"
	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
)

// Dataset is a deterministic in-memory training set. It has explicit
// batch boundaries and no hidden state, so two runs over the same data
// visit the batches in the same order.
type Dataset struct {
	// Inputs is [N, ...] stacked examples.
	Inputs *tensor.Tensor
	// Targets is [N, ...] stacked targets.
	Targets *tensor.Tensor
}

// NewDataset validates that inputs and targets agree on the batch dim.
func NewDataset(inputs, targets *tensor.Tensor) (*Dataset, error) {
	if inputs == nil || targets == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "dataset tensors must not be nil")
	}
	if inputs.Shape().Rank() == 0 || targets.Shape().Rank() == 0 {
		return nil, errors.New(errors.CodeInvalidArgument, "dataset tensors must have a batch dim")
	}
	if inputs.Shape().Dim(0) != targets.Shape().Dim(0) {
		return nil, errors.New(errors.CodeShapeMismatch, "dataset batch mismatch").
			WithField("inputs", inputs.Shape().Dim(0)).
			WithField("targets", targets.Shape().Dim(0))
	}
	return &Dataset{Inputs: inputs, Targets: targets}, nil
}

// Len returns the number of examples.
func (d *Dataset) Len() int { return d.Inputs.Shape().Dim(0) }

// Batch returns the i-th slice of the dataset as fresh tensors. Slices
// are views; callers that mutate must copy first. The returned tensors
// keep the dataset's storage alive, which is bounded by the dataset, not
// by the number of batches taken.
func (d *Dataset) Batch(i, size int) (*tensor.Tensor, *tensor.Tensor, error) {
	if size <= 0 {
		return nil, nil, errTrainerConfig("batch size must be positive")
	}
	n := d.Len()
	if i < 0 || i >= n {
		return nil, nil, errors.New(errors.CodeOutOfRange, "batch index out of range").
			WithField("index", i).WithField("examples", n)
	}
	end := i + size
	if end > n {
		end = n
	}
	in, err := d.Inputs.Slice([]int{i, 0}, []int{end, d.Inputs.Shape().Dim(1)})
	if err != nil {
		return nil, nil, err
	}
	tg, err := d.Targets.Slice([]int{i, 0}, []int{end, d.Targets.Shape().Dim(1)})
	if err != nil {
		return nil, nil, err
	}
	return in, tg, nil
}

// BatchCount returns the number of batches of the given size.
func (d *Dataset) BatchCount(size int) int {
	if size <= 0 {
		return 0
	}
	n := d.Len()
	return (n + size - 1) / size
}

// TrainConfig fully determines a training run: same config + same data
// => same trajectory (within documented float determinism).
type TrainConfig struct {
	// Seed seeds weight init and any stochastic data order.
	Seed int64
	// Steps is the number of optimizer steps.
	Steps int
	// BatchSize bounds each step's examples.
	BatchSize int
	// Optimizer selects the update rule.
	Optimizer OptimizerKind
	// LRSchedule maps step index to learning rate.
	LRSchedule Schedule
	// Loss selects the differentiable loss.
	Loss LossKind
	// ClipGradNorm clips the global gradient norm when > 0.
	ClipGradNorm float64
	// CheckpointPath, when set, receives a checkpoint after training.
	CheckpointPath string
	// ModelName is recorded in the checkpoint.
	ModelName string
}

// OptimizerKind identifies the optimizer used for a run.
type OptimizerKind int

// Supported optimizer kinds.
const (
	OptimizerSGD OptimizerKind = iota
	OptimizerAdam
)

// String names the kind for logs and checkpoints.
func (k OptimizerKind) String() string {
	switch k {
	case OptimizerSGD:
		return "sgd"
	case OptimizerAdam:
		return "adam"
	}
	return "unknown"
}

// LossKind identifies the loss used for a run.
type LossKind int

// Supported loss kinds.
const (
	LossMSE LossKind = iota
)

// String names the kind for logs and checkpoints.
func (k LossKind) String() string {
	switch k {
	case LossMSE:
		return "mse"
	}
	return "unknown"
}

// Validate reports the first configuration problem.
func (c TrainConfig) Validate() error {
	if c.Steps <= 0 {
		return errTrainerConfig("steps must be positive")
	}
	if c.BatchSize <= 0 {
		return errTrainerConfig("batch size must be positive")
	}
	if err := validateSchedule(c.LRSchedule); err != nil {
		return err
	}
	switch c.Optimizer {
	case OptimizerSGD, OptimizerAdam:
	default:
		return errTrainerConfig("unknown optimizer")
	}
	switch c.Loss {
	case LossMSE:
	default:
		return errTrainerConfig("unknown loss")
	}
	if c.ClipGradNorm < 0 {
		return errTrainerConfig("clip norm must be non-negative")
	}
	return nil
}

// StepMetrics records one training step for logs and checkpoints.
type StepMetrics struct {
	Step        int     `json:"step"`
	Loss        float64 `json:"loss"`
	GradNorm    float64 `json:"grad_norm"`
	LearningRate float64 `json:"learning_rate"`
}

// TrainResult summarizes a completed run.
type TrainResult struct {
	Steps       int           `json:"steps"`
	FinalLoss   float64       `json:"final_loss"`
	Metrics     []StepMetrics  `json:"metrics"`
	ElapsedNanos int64         `json:"elapsed_ns"`
}

// Trainer runs deterministic training loops and persists training state
// (parameters + optimizer state + step counter) so a resumed run
// continues exactly where an uninterrupted run left off.
type Trainer struct {
	Config TrainConfig
	Module Module
	opt    autograd.Optimizer
	step   int
	adam   *autograd.Adam
	sgd    *autograd.SGD
}

// NewTrainer validates the config and builds the optimizer.
func NewTrainer(m Module, cfg TrainConfig) (*Trainer, error) {
	if m == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "trainer requires a module")
	}
	if err := cfg.Validate(); err != nil {
		return nil, err
	}
	t := &Trainer{Config: cfg, Module: m, step: 0}
	initLR := cfg.LRSchedule.LR(0)
	switch cfg.Optimizer {
	case OptimizerSGD:
		s, err := autograd.NewSGD(initLR, 0) // per-step LR comes from the schedule
		if err != nil {
			return nil, err
		}
		t.sgd = s
		t.opt = s
	case OptimizerAdam:
		a, err := autograd.NewAdam(initLR, 0.9, 0.999, 1e-8)
		if err != nil {
			return nil, err
		}
		t.adam = a
		t.opt = a
	}
	return t, nil
}

// Step performs one optimizer step and returns its metrics. The caller
// owns the tape: each step builds a fresh tape, so no graph is retained
// between steps.
func (t *Trainer) Step(ds *Dataset, batchIndex int) (StepMetrics, error) {
	if ds == nil {
		return StepMetrics{}, errNoData()
	}
	in, tg, err := ds.Batch(batchIndex, t.Config.BatchSize)
	if err != nil {
		return StepMetrics{}, err
	}
	x := autograd.NewVariable(in, false)
	y := autograd.NewVariable(tg, false)

	tape := autograd.NewTape()
	pred, err := t.Module.Forward(tape, x)
	if err != nil {
		return StepMetrics{}, errors.Wrap(err, errors.CodeInternal, "forward")
	}
	loss, err := lossFor(tape, t.Config.Loss, pred, y)
	if err != nil {
		return StepMetrics{}, err
	}
	lossVal := loss.Value.Float64()[0]
	if err := tape.Backward(nil); err != nil {
		return StepMetrics{}, errors.Wrap(err, errors.CodeInternal, "backward")
	}
	vars := t.Module.Parameters()
	norm, err := autograd.GradNorm(vars)
	if err != nil {
		return StepMetrics{}, err
	}
	if t.Config.ClipGradNorm > 0 {
		if _, err := autograd.ClipGradients(vars, t.Config.ClipGradNorm); err != nil {
			return StepMetrics{}, errors.Wrap(err, errors.CodeInternal, "clip")
		}
	}
	lr := t.Config.LRSchedule.LR(t.step)
	t.applyLR(lr)
	if err := t.opt.Step(vars); err != nil {
		return StepMetrics{}, errors.Wrap(err, errors.CodeInternal, "optimizer step")
	}
	t.step++
	return StepMetrics{Step: t.step - 1, Loss: lossVal, GradNorm: norm, LearningRate: lr}, nil
}

func (t *Trainer) applyLR(lr float64) {
	switch {
	case t.sgd != nil:
		t.sgd.LR = lr
	case t.adam != nil:
		t.adam.LR = lr
	}
}

func lossFor(tape *autograd.Tape, kind LossKind, pred, target *autograd.Variable) (*autograd.Variable, error) {
	switch kind {
	case LossMSE:
		return MSELoss(tape, pred, target)
	}
	return nil, errTrainerConfig("unknown loss")
}

// Train runs Steps steps over the dataset, cycling batches
// deterministically, and returns the metrics. Gradients are zeroed at
// the start of each step.
func (t *Trainer) Train(ds *Dataset) (*TrainResult, error) {
	if ds == nil {
		return nil, errNoData()
	}
	batches := ds.BatchCount(t.Config.BatchSize)
	if batches == 0 {
		return nil, errTrainerConfig("batch size exceeds dataset")
	}
	result := &TrainResult{Steps: t.Config.Steps}
	for i := 0; i < t.Config.Steps; i++ {
		for _, v := range t.Module.Parameters() {
			v.ZeroGrad()
		}
		m, err := t.Step(ds, i%batches)
		if err != nil {
			return nil, err
		}
		result.Metrics = append(result.Metrics, m)
		result.FinalLoss = m.Loss
	}
	if t.Config.CheckpointPath != "" {
		cp, err := t.Checkpoint()
		if err != nil {
			return nil, err
		}
		if err := checkpoint.WriteFile(t.Config.CheckpointPath, cp); err != nil {
			return nil, errors.Wrap(err, errors.CodeInternal, "write checkpoint")
		}
	}
	return result, nil
}

// Step returns the number of completed steps.
func (t *Trainer) StepCount() int { return t.step }

// Checkpoint snapshots the full training state: parameters, optimizer
// state (moments and step counter), the schedule name, and the config
// seed, so a restored trainer reproduces the trajectory.
func (t *Trainer) Checkpoint() (*checkpoint.FileCheckpoint, error) {
	cp, err := ToCheckpoint(t.Config.ModelName, t.Module)
	if err != nil {
		return nil, err
	}
	if cp.Metadata == nil {
		cp.Metadata = map[string]string{}
	}
	cp.Metadata["optimizer"] = t.Config.Optimizer.String()
	cp.Metadata["schedule"] = t.Config.LRSchedule.Name()
	cp.Metadata["loss"] = t.Config.Loss.String()
	cp.Metadata["seed"] = fmt.Sprint(t.Config.Seed)
	cp.Metadata["clip_grad_norm"] = fmt.Sprint(t.Config.ClipGradNorm)
	cp.Optimizer = &checkpoint.OptimizerState{
		Kind: "" + t.Config.Optimizer.String(),
		Step: int64(t.step),
	}
	return cp, nil
}

// Restore loads parameters and optimizer state from cp into the trainer.
// It refuses checkpoints whose optimizer kind does not match, because
// restoring Adam moments into an SGD trainer would silently change the
// update rule.
func (t *Trainer) Restore(cp *checkpoint.FileCheckpoint) error {
	if cp == nil {
		return errors.New(errors.CodeInvalidArgument, "nil checkpoint")
	}
	if cp.Optimizer != nil && cp.Optimizer.Kind != "" && cp.Optimizer.Kind != t.Config.Optimizer.String() {
		return errors.New(errors.CodeInvalidArgument,
			"checkpoint optimizer kind does not match the trainer").
			WithField("checkpoint", cp.Optimizer.Kind).
			WithField("trainer", t.Config.Optimizer.String())
	}
	if err := RestoreFromCheckpoint(t.Module, cp); err != nil {
		return err
	}
	if cp.Optimizer != nil {
		t.step = int(cp.Optimizer.Step)
	}
	return nil
}
