// Package distributed provides pipeline parallelism implementation.
package distributed

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"github.com/astrovox/astrovox/tensor"
)

var (
	ErrPipelineStalled = errors.New("pipeline stalled")
	ErrInvalidStage    = errors.New("invalid pipeline stage")
	ErrMicrobatchSize  = errors.New("invalid microbatch size")
)

// PipelineParallelConfig holds pipeline parallelism configuration.
type PipelineParallelConfig struct {
	NumStages            int          // Number of pipeline stages
	NumMicrobatches      int          // Number of microbatches
	VirtualStages        int          // Virtual pipeline stages per rank (for 1F1B)
	Schedule             ScheduleType // Pipeline schedule
	OverlapComm          bool         // Overlap communication with computation
	ActivationCheckpoint bool         // Checkpoint activations for memory
}

// ScheduleType defines the pipeline schedule.
type ScheduleType int

const (
	ScheduleGPipe       ScheduleType = iota // GPipe schedule
	Schedule1F1B                            // 1F1B (One Forward One Backward)
	ScheduleInterleaved                     // Interleaved 1F1B
	ScheduleZeroBubble                      // Zero-bubble schedule
)

// PipelineStage represents a single pipeline stage.
type PipelineStage struct {
	stageID    int
	numStages  int
	rank       int
	modelChunk ModelChunk
	recvOps    []*CommOp
	sendOps    []*CommOp
	buffers    []*ActivationBuffer
	mu         sync.Mutex
}

// ModelChunk is a portion of the model assigned to a stage.
type ModelChunk interface {
	Forward(ctx context.Context, input *tensor.Tensor) (*tensor.Tensor, error)
	Backward(ctx context.Context, gradOutput *tensor.Tensor) (*tensor.Tensor, error)
	Parameters() []*tensor.Tensor
	NamedParameters() map[string]*tensor.Tensor
}

// ActivationBuffer stores activations for backward pass.
type ActivationBuffer struct {
	data       *tensor.Tensor
	microbatch int
	refCount   atomic.Int32
}

// CommOp represents a communication operation.
type CommOp struct {
	opType   string // "send", "recv", "send_recv"
	peerRank int
	tensor   *tensor.Tensor
	done     chan error
	async    bool
}

// PipelineParallel manages pipeline parallel execution.
type PipelineParallel struct {
	config    *PipelineParallelConfig
	stages    []*PipelineStage
	stageID   int
	numStages int
	rank      int
	worldSize int
	group     *ProcessGroup
	scheduler *PipelineScheduler
	mu        sync.RWMutex
	running   atomic.Bool
	stats     PipelineStats
}

// PipelineScheduler orchestrates pipeline execution.
type PipelineScheduler struct {
	config          *PipelineParallelConfig
	numStages       int
	numMicrobatches int
	schedule        ScheduleType

	// State tracking
	forwardQueue   chan *PipelineTask
	backwardQueue  chan *PipelineTask
	activeForward  map[int]*PipelineTask
	activeBackward map[int]*PipelineTask

	// Synchronization
	stageBarriers  []chan struct{}
	microbatchDone chan int

	// Stats
	mu        sync.Mutex
	completed int
	bubbles   int
	stallTime time.Duration
}

// PipelineTask represents a microbatch task.
type PipelineTask struct {
	microbatchID int
	stageID      int
	input        *tensor.Tensor
	output       *tensor.Tensor
	gradOutput   *tensor.Tensor
	gradInput    *tensor.Tensor
	activations  []*ActivationBuffer
	isForward    bool
	done         chan error
	startTime    time.Time
}

// PipelineStats tracks pipeline statistics.
type PipelineStats struct {
	TotalMicrobatches int64
	CompletedForward  int64
	CompletedBackward int64
	Bubbles           int64
	StallTimeNs       int64
	AvgStageTimeNs    int64
}

// NewPipelineParallel creates a new pipeline parallel wrapper.
func NewPipelineParallel(config *PipelineParallelConfig, group *ProcessGroup) (*PipelineParallel, error) {
	if config.NumStages <= 1 {
		return nil, ErrInvalidStage
	}
	if config.NumMicrobatches <= 0 {
		return nil, ErrMicrobatchSize
	}
	if group.WorldSize() != config.NumStages {
		return nil, ErrInvalidStage
	}

	rank := group.Rank()

	pp := &PipelineParallel{
		config:    config,
		stageID:   rank,
		numStages: config.NumStages,
		rank:      rank,
		worldSize: config.NumStages,
		group:     group,
		scheduler: NewPipelineScheduler(config),
	}

	// Initialize stages
	pp.stages = make([]*PipelineStage, config.NumStages)
	for i := 0; i < config.NumStages; i++ {
		pp.stages[i] = &PipelineStage{
			stageID:   i,
			numStages: config.NumStages,
			rank:      rank,
		}
	}

	return pp, nil
}

// NewPipelineScheduler creates a new pipeline scheduler.
func NewPipelineScheduler(config *PipelineParallelConfig) *PipelineScheduler {
	return &PipelineScheduler{
		config:          config,
		numStages:       config.NumStages,
		numMicrobatches: config.NumMicrobatches,
		schedule:        config.Schedule,
		forwardQueue:    make(chan *PipelineTask, config.NumMicrobatches*config.NumStages),
		backwardQueue:   make(chan *PipelineTask, config.NumMicrobatches*config.NumStages),
		activeForward:   make(map[int]*PipelineTask),
		activeBackward:  make(map[int]*PipelineTask),
		stageBarriers:   make([]chan struct{}, config.NumStages),
		microbatchDone:  make(chan int, config.NumMicrobatches),
	}
}

// AssignModelChunk assigns a model chunk to this stage.
func (pp *PipelineParallel) AssignModelChunk(chunk ModelChunk) {
	if pp.stageID < len(pp.stages) {
		pp.stages[pp.stageID].modelChunk = chunk
	}
}

// Execute runs the pipeline on a batch of inputs.
func (pp *PipelineParallel) Execute(ctx context.Context, inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
	if len(inputs) != pp.config.NumMicrobatches {
		return nil, ErrMicrobatchSize
	}

	pp.running.Store(true)
	defer pp.running.Store(false)

	var outputs []*tensor.Tensor
	var err error

	switch pp.config.Schedule {
	case ScheduleGPipe:
		outputs, err = pp.executeGPipe(ctx, inputs)
	case Schedule1F1B:
		outputs, err = pp.execute1F1B(ctx, inputs)
	case ScheduleInterleaved:
		outputs, err = pp.executeInterleaved(ctx, inputs)
	default:
		return nil, fmt.Errorf("unsupported schedule: %v", pp.config.Schedule)
	}

	return outputs, err
}

// executeGPipe runs the GPipe schedule (simple: all forward, then all backward).
func (pp *PipelineParallel) executeGPipe(ctx context.Context, inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
	var outputs []*tensor.Tensor
	activations := make([][]*ActivationBuffer, pp.config.NumMicrobatches)

	// Pipeline forward
	for mb := 0; mb < pp.config.NumMicrobatches; mb++ {
		input := inputs[mb]
		stageActivations := make([]*ActivationBuffer, pp.numStages)

		for s := 0; s < pp.numStages; s++ {
			stage := pp.stages[s]

			// Receive from previous stage (except first stage)
			if s > 0 {
				// input = recv from stage s-1
				input = pp.recvFromPrev(ctx, s, mb)
			}

			// Forward through model chunk
			if stage.modelChunk != nil && s == pp.stageID {
				var act *ActivationBuffer
				output, err := stage.modelChunk.Forward(ctx, input)
				if err != nil {
					return nil, err
				}

				// Store activation for backward
				if pp.config.ActivationCheckpoint {
					cloned, err := output.Clone()
					if err != nil {
						return nil, err
					}
					act = &ActivationBuffer{data: cloned}
				} else {
					act = &ActivationBuffer{data: output}
				}
				act.microbatch = mb
				stageActivations[s] = act

				input = output
			}

			// Send to next stage (except last stage)
			if s < pp.numStages-1 {
				pp.sendToNext(ctx, s, mb, input)
			}
		}

		activations[mb] = stageActivations

		// Collect output from last stage
		if pp.stageID == pp.numStages-1 {
			outputs = append(outputs, input)
		}
	}

	// Backward pass
	for mb := pp.config.NumMicrobatches - 1; mb >= 0; mb-- {
		// Would compute gradients
	}

	return outputs, nil
}

// execute1F1B runs the 1F1B schedule. The 1F1B interleaving needs async
// collectives, so this falls back to the GPipe ordering for now; the
// warmup count is retained to document the intended schedule.
func (pp *PipelineParallel) execute1F1B(ctx context.Context, inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
	warmup := pp.numStages - 1 - pp.stageID
	if warmup < 0 {
		warmup = 0
	}
	_ = warmup

	return pp.executeGPipe(ctx, inputs)
}

// executeInterleaved runs interleaved 1F1B (for virtual stages).
func (pp *PipelineParallel) executeInterleaved(ctx context.Context, inputs []*tensor.Tensor) ([]*tensor.Tensor, error) {
	// Each rank has multiple model chunks (virtual stages)
	// Schedule interleaves forward/backward across virtual stages
	return pp.execute1F1B(ctx, inputs)
}

func (pp *PipelineParallel) recvFromPrev(ctx context.Context, stage, mb int) *tensor.Tensor {
	// Receive tensor from previous stage
	// In practice, would use non-blocking recv
	t, _ := tensor.New(tensor.Float64, []int{1, 1}) // Placeholder
	return t
}

func (pp *PipelineParallel) sendToNext(ctx context.Context, stage, mb int, t *tensor.Tensor) {
	// Send tensor to next stage
	// In practice, would use non-blocking send
}

// PipelineRuntime provides a higher-level pipeline execution interface.
type PipelineRuntime struct {
	*PipelineParallel
	model      Model
	optimizer  Optimizer
	lossFn     LossFn
	gradScaler *GradScaler
}

// Model interface for pipeline execution.
type Model interface {
	Forward(ctx context.Context, input *tensor.Tensor) (*tensor.Tensor, error)
	Backward(ctx context.Context, gradOutput *tensor.Tensor) error
	Parameters() []*tensor.Tensor
	ZeroGrad()
}

// Optimizer interface.
type Optimizer interface {
	Step()
	ZeroGrad()
}

// LossFn computes loss.
type LossFn func(output, target *tensor.Tensor) (*tensor.Tensor, error)

// GradScaler handles gradient scaling for mixed precision.
type GradScaler struct {
	scale    float64
	growth   float64
	backoff  float64
	minScale float64
	enabled  bool
}

func NewGradScaler(initScale float64) *GradScaler {
	return &GradScaler{
		scale:    initScale,
		growth:   2.0,
		backoff:  0.5,
		minScale: 1.0,
		enabled:  true,
	}
}

func (gs *GradScaler) Scale(loss *tensor.Tensor) *tensor.Tensor {
	if !gs.enabled {
		return loss
	}
	// loss *= scale
	return loss
}

func (gs *GradScaler) Unscale(grads []*tensor.Tensor) bool {
	if !gs.enabled {
		return true
	}
	// Check for inf/nan, update scale
	return true
}

// TrainStep executes one training step with pipeline parallelism.
func (pr *PipelineRuntime) TrainStep(ctx context.Context, inputs, targets []*tensor.Tensor) (float64, error) {
	// Forward pass
	outputs, err := pr.Execute(ctx, inputs)
	if err != nil {
		return 0, err
	}

	// Compute loss
	totalLoss := 0.0
	gradOutputs := make([]*tensor.Tensor, len(outputs))

	for i, out := range outputs {
		loss, err := pr.lossFn(out, targets[i])
		if err != nil {
			return 0, err
		}
		totalLoss += loss.Float64()[0]

		// Compute gradient of loss w.r.t. output
		// gradOutputs[i] = dLoss/dOutput
		gradOutputs[i] = loss // Simplified
	}

	// Backward pass (would need to be implemented)
	// pr.Backward(ctx, gradOutputs)

	// Optimizer step
	// pr.optimizer.Step()

	return totalLoss / float64(len(outputs)), nil
}

// PipelineProfiler profiles pipeline execution.
type PipelineProfiler struct {
	stageTimes  [][]time.Duration
	commTimes   [][]time.Duration
	bubbleTimes []time.Duration
	mu          sync.Mutex
}

func NewPipelineProfiler(numStages, numMicrobatches int) *PipelineProfiler {
	return &PipelineProfiler{
		stageTimes:  make([][]time.Duration, numStages),
		commTimes:   make([][]time.Duration, numStages),
		bubbleTimes: make([]time.Duration, 0),
	}
}

func (pp *PipelineProfiler) RecordStageTime(stage, mb int, d time.Duration) {
	pp.mu.Lock()
	defer pp.mu.Unlock()
	if len(pp.stageTimes[stage]) <= mb {
		pp.stageTimes[stage] = append(pp.stageTimes[stage], make([]time.Duration, mb+1-len(pp.stageTimes[stage]))...)
	}
	pp.stageTimes[stage][mb] = d
}

func (pp *PipelineProfiler) GetStats() map[string]interface{} {
	pp.mu.Lock()
	defer pp.mu.Unlock()

	stats := make(map[string]interface{})
	for s := 0; s < len(pp.stageTimes); s++ {
		var total time.Duration
		for _, d := range pp.stageTimes[s] {
			total += d
		}
		stats[fmt.Sprintf("stage_%d_avg_ms", s)] = float64(total.Milliseconds()) / float64(len(pp.stageTimes[s]))
	}
	return stats
}
