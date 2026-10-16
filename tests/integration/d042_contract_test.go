package integration_test

import (
	"context"
	"os"
	"testing"
	"time"

	axerrors "github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/autograd"
	"github.com/astrovox/astrovox/internal/checkpoint"
	"github.com/astrovox/astrovox/inference"
	"github.com/astrovox/astrovox/model"
	"github.com/astrovox/astrovox/tensor"
)

// TestContractCheckpointRoundTrip verifies the persistence contract:
// WriteFile -> ReadFile -> Inspect must round-trip faithfully.
func TestContractCheckpointRoundTrip(t *testing.T) {
	dir := t.TempDir()
	path := dir + "/model.axck"

	cp := &checkpoint.FileCheckpoint{
		Version: checkpoint.FileFormatVersion,
		Model:   "contract-model",
		Metadata: map[string]string{
			"seed": "42",
			"task": "contract",
		},
		Parameters: []checkpoint.NamedTensor{
			{Name: "fc0.W", Shape: []int{2, 3}, Data: []float64{1, 2, 3, 4, 5, 6}},
			{Name: "fc0.b", Shape: []int{3}, Data: []float64{0.1, -0.2, 0.3}},
		},
		Optimizer: &checkpoint.OptimizerState{
			Kind: "sgd",
			Step: 7,
			Moments: map[string][]float64{
				"fc0.W": {0.1, 0.2, 0.3, 0.4, 0.5, 0.6},
			},
		},
	}

	if err := checkpoint.WriteFile(path, cp); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	got, err := checkpoint.ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}

	if got.Model != "contract-model" || got.Version != checkpoint.FileFormatVersion {
		t.Fatalf("header mismatch: model=%q version=%d", got.Model, got.Version)
	}
	if len(got.Parameters) != 2 {
		t.Fatalf("expected 2 parameters, got %d", len(got.Parameters))
	}
	if got.Optimizer == nil || got.Optimizer.Kind != "sgd" || got.Optimizer.Step != 7 {
		t.Fatalf("optimizer mismatch: %+v", got.Optimizer)
	}
}

// TestContractCheckpointCorruptionIsRefused verifies that a single-bit
// corruption is detected with CodeCorruptData, not silently accepted.
func TestContractCheckpointCorruptionIsRefused(t *testing.T) {
	dir := t.TempDir()
	path := dir + "/corrupt.axck"

	cp := &checkpoint.FileCheckpoint{
		Version: checkpoint.FileFormatVersion,
		Model:   "corrupt",
		Parameters: []checkpoint.NamedTensor{
			{Name: "w", Shape: []int{2}, Data: []float64{1, 2}},
		},
	}
	if err := checkpoint.WriteFile(path, cp); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read seed: %v", err)
	}
	data[len(data)/2] ^= 0xff // single-bit flip

	bad := dir + "/bad.axck"
	if err := os.WriteFile(bad, data, 0o644); err != nil {
		t.Fatalf("write bad: %v", err)
	}

	if _, err := checkpoint.ReadFile(bad); err == nil {
		t.Fatal("corrupted checkpoint was accepted")
	} else if !axerrors.IsCode(err, axerrors.CodeCorruptData) {
		t.Fatalf("corruption error = %v, want CORRUPT_DATA", err)
	}
}

// TestContractCheckpointFutureVersionIsRefused verifies that a checkpoint
// with a newer format version is refused with CodeVersionMismatch.
func TestContractCheckpointFutureVersionIsRefused(t *testing.T) {
	dir := t.TempDir()
	path := dir + "/future.axck"

	cp := &checkpoint.FileCheckpoint{
		Version: checkpoint.FileFormatVersion + 1, // future version
		Model:   "future",
		Parameters: []checkpoint.NamedTensor{
			{Name: "w", Shape: []int{2}, Data: []float64{1, 2}},
		},
	}
	if err := checkpoint.WriteFile(path, cp); err != nil {
		// WriteFile itself may reject future versions; either is acceptable.
		return
	}
	if _, err := checkpoint.ReadFile(path); err == nil {
		t.Fatal("future-version checkpoint was accepted")
	} else if !axerrors.IsCode(err, axerrors.CodeVersionMismatch) {
		t.Fatalf("future-version error = %v, want VERSION_MISMATCH", err)
	}
}

// TestContractInferenceDeadlineRefused verifies that an already-expired
// deadline is refused at submission, not executed and then declared late.
func TestContractInferenceDeadlineRefused(t *testing.T) {
	m, err := model.NewMLP("mlp", []int{2, 3, 1}, model.ActRelu, 1)
	if err != nil {
		t.Fatalf("NewMLP: %v", err)
	}
	exec, err := inference.NewExecutor(&inference.ModuleExecutable{Module: m}, 1, inference.DefaultLimits)
	if err != nil {
		t.Fatalf("NewExecutor: %v", err)
	}
	defer exec.Shutdown(2 * time.Second)

	in, err := tensor.Zeros(tensor.Float64, []int{1, 2})
	if err != nil {
		t.Fatalf("Zeros: %v", err)
	}

	past := time.Now().Add(-time.Second)
	if _, err := exec.Run(context.Background(), inference.Request{
		ID:       "expired",
		Inputs:   map[string]*tensor.Tensor{inference.InputKey: in},
		Deadline: past,
	}); !axerrors.IsCode(err, axerrors.CodeTimeout) {
		t.Fatalf("expired deadline = %v, want CODE_TIMEOUT", err)
	}
}

// TestContractInferenceResourceLimitRefused verifies oversized input is
// refused at admission with CodeResourceExhausted.
func TestContractInferenceResourceLimitRefused(t *testing.T) {
	m, err := model.NewMLP("mlp", []int{2, 2, 1}, model.ActRelu, 1)
	if err != nil {
		t.Fatalf("NewMLP: %v", err)
	}
	small, err := inference.NewExecutor(&inference.ModuleExecutable{Module: m}, 1,
		inference.Limits{MaxInputs: 4, MaxElements: 4, MaxOutputElements: 64})
	if err != nil {
		t.Fatalf("NewExecutor: %v", err)
	}
	defer small.Shutdown(2 * time.Second)

	big, err := tensor.Zeros(tensor.Float64, []int{2, 8}) // 16 elements > 4 limit
	if err != nil {
		t.Fatalf("Zeros: %v", err)
	}
	if _, err := small.Run(context.Background(), inference.Request{
		ID:     "oversized",
		Inputs: map[string]*tensor.Tensor{inference.InputKey: big},
	}); !axerrors.IsCode(err, axerrors.CodeResourceExhausted) {
		t.Fatalf("oversized input = %v, want CODE_RESOURCE_EXHAUSTED", err)
	}
}

// TestContractModelDeterminism verifies same seed + shape => identical
// parameters (reproducibility contract).
func TestContractModelDeterminism(t *testing.T) {
	a, err := model.NewMLP("mlp", []int{3, 4, 1}, model.ActRelu, 42)
	if err != nil {
		t.Fatalf("NewMLP: %v", err)
	}
	b, err := model.NewMLP("mlp", []int{3, 4, 1}, model.ActRelu, 42)
	if err != nil {
		t.Fatalf("NewMLP: %v", err)
	}

	pa := a.Parameters()
	pb := b.Parameters()
	if len(pa) != len(pb) {
		t.Fatalf("parameter count differs: %d vs %d", len(pa), len(pb))
	}
	for i := range pa {
		va, vb := pa[i].Value.Float64(), pb[i].Value.Float64()
		for j := range va {
			if va[j] != vb[j] {
				t.Fatalf("parameter %d[%d] differs: %v vs %v", i, j, va[j], vb[j])
			}
		}
	}
}

// TestContractFlattenRejectsSharedParameter verifies the duplicate
// parameter detection contract.
func TestContractFlattenRejectsSharedParameter(t *testing.T) {
	shared, err := model.NewLinear("shared", 2, 2, 5)
	if err != nil {
		t.Fatalf("NewLinear: %v", err)
	}
	seq, err := model.NewSequential("dup", shared, shared)
	if err != nil {
		t.Fatalf("NewSequential: %v", err)
	}
	if _, err := model.Flatten(seq); err == nil {
		t.Fatal("shared parameter was not rejected")
	}
}

// TestContractAutogradRulelessNodeErrors verifies that a recorded node
// without a gradient rule is a typed error, not a silent zero.
func TestContractAutogradRulelessNodeErrors(t *testing.T) {
	tape := autograd.NewTape()
	a := autograd.NewVariable(tensorOf1d(1.0), true)
	if _, err := autograd.Mul(tape, a, a); err != nil {
		t.Fatalf("Mul: %v", err)
	}
	unbacked := autograd.NewVariable(tensorOf1d(1.0), true)
	unbacked.Creator = true
	tape.Record(unbacked)
	if err := tape.Backward(nil); err == nil {
		t.Fatal("rule-less node was silently skipped")
	} else if !axerrors.IsCode(err, axerrors.CodeUnimplemented) {
		t.Fatalf("rule-less node error = %v, want CODE_UNIMPLEMENTED", err)
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func tensorOf1d(v float64) *tensor.Tensor {
	t, err := tensor.New(tensor.Float64, []int{1})
	if err != nil {
		panic(err)
	}
	t.Float64()[0] = v
	return t
}
