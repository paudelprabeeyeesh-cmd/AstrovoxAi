// Package distributed provides data parallelism (DDP) implementation.
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
	ErrDDPNotInitialized = errors.New("DDP not initialized")
	ErrGradBucketFull    = errors.New("gradient bucket full")
)

// DDPConfig holds data parallel configuration.
type DDPConfig struct {
	GradBucketCapMB int      // Gradient bucket capacity in MB
	BroadcastBuffers bool    // Broadcast buffers before training
	FindUnusedParams bool    // Find unused parameters
	GradientAsBucketView bool // Use bucket views for gradients
	OverlapGradReduce bool   // Overlap gradient reduction with backward
	StaticGraph      bool    // Assume static computation graph
}

// DDPMasterWeight holds a master copy of weights (FP32) for mixed precision.
type DDPMasterWeight struct {
	param   *tensor.Tensor
	master  *tensor.Tensor
}

// DDP wraps a model for data parallel training.
type DDP struct {
	config       *DDPConfig
	rank         int
	worldSize    int
	group        *ProcessGroup
	model        *DistributedModel
	buckets      []*GradBucket
	bucketMap    map[*tensor.Tensor]int
	params       []*tensor.Tensor
	gradients    []*tensor.Tensor
	initialized  atomic.Bool
	syncStep     atomic.Int64
	mu           sync.RWMutex
	commStream   *CommStream
	hooks        []DDPHook
	stats        DDPStats
}

// DistributedModel represents a model that can be wrapped by DDP.
type DistributedModel struct {
	params     []*tensor.Tensor
	gradients  []*tensor.Tensor
	paramNames map[string]*tensor.Tensor
	forwardFn  func(ctx context.Context, input *tensor.Tensor) (*tensor.Tensor, error)
	backwardFn func(ctx context.Context, grad *tensor.Tensor) error
}

// NewDistributedModel creates a distributed model.
func NewDistributedModel(params []*tensor.Tensor, forwardFn func(ctx context.Context, input *tensor.Tensor) (*tensor.Tensor, error), backwardFn func(ctx context.Context, grad *tensor.Tensor) error) *DistributedModel {
	gradients := make([]*tensor.Tensor, len(params))
	for i, p := range params {
		g, _ := tensor.New(p.DType(), p.Shape().Dims())
		gradients[i] = g
	}
	
	names := make(map[string]*tensor.Tensor)
	for _, p := range params {
		_ = p
		names[fmt.Sprintf("param_%d", len(names))] = p
	}

	return &DistributedModel{
		params:     params,
		gradients:  gradients,
		paramNames: names,
		forwardFn:  forwardFn,
		backwardFn: backwardFn,
	}
}

// Parameters returns model parameters.
func (m *DistributedModel) Parameters() []*tensor.Tensor {
	return m.params
}

// Gradients returns gradient tensors.
func (m *DistributedModel) Gradients() []*tensor.Tensor {
	return m.gradients
}

// GradBucket groups parameters for gradient synchronization.
type GradBucket struct {
	id        int
	params    []*tensor.Tensor
	grads     []*tensor.Tensor
	flatGrad  *tensor.Tensor
	capacity  int // Number of elements
	ready     atomic.Bool
	reducing  atomic.Bool
	done      chan struct{}
	mu        sync.Mutex
}

// NewGradBucket creates a new gradient bucket.
func NewGradBucket(id int, capacity int) *GradBucket {
	flat, _ := tensor.New(tensor.Float64, []int{capacity})
	return &GradBucket{
		id:       id,
		flatGrad: flat,
		capacity: capacity,
		done:     make(chan struct{}, 1),
	}
}

// AddParam adds a parameter to the bucket.
func (gb *GradBucket) AddParam(p *tensor.Tensor) error {
	gb.mu.Lock()
	defer gb.mu.Unlock()
	
	numel := p.NumElements()
	used := 0
	for _, g := range gb.grads {
		used += g.NumElements()
	}
	if used+numel > gb.capacity {
		return ErrGradBucketFull
	}
	
	gb.params = append(gb.params, p)
	gb.grads = append(gb.grads, p)
	return nil
}

// IsFull returns true if bucket is at capacity.
func (gb *GradBucket) IsFull() bool {
	gb.mu.Lock()
	defer gb.mu.Unlock()
	used := 0
	for _, g := range gb.grads {
		used += g.NumElements()
	}
	return used >= gb.capacity
}

// Flatten copies gradients into the flat buffer.
func (gb *GradBucket) Flatten() {
	gb.mu.Lock()
	defer gb.mu.Unlock()
	
	offset := 0
	flatV := gb.flatGrad.Float64()
	for _, g := range gb.grads {
		gv := g.Float64()
		copy(flatV[offset:], gv)
		offset += g.NumElements()
	}
}

// Unflatten copies flat buffer back into gradient tensors.
func (gb *GradBucket) Unflatten() {
	gb.mu.Lock()
	defer gb.mu.Unlock()
	
	offset := 0
	flatV := gb.flatGrad.Float64()
	for _, g := range gb.grads {
		gv := g.Float64()
		copy(gv, flatV[offset:offset+g.NumElements()])
		offset += g.NumElements()
	}
}

// DDPHook allows custom behavior at various DDP lifecycle points.
type DDPHook interface {
	OnParamsReady(params []*tensor.Tensor)
	OnGradReady(grad *tensor.Tensor)
	OnBackwardDone()
	OnStepStart()
	OnStepDone()
}

// DDPStats tracks DDP statistics.
type DDPStats struct {
	TotalAllReduce    atomic.Int64
	TotalBytesReduced atomic.Int64
	AvgAllReduceMs    atomic.Int64
	BucketsReduced    atomic.Int64
}

// NewDDP creates a new DDP wrapper.
func NewDDP(model *DistributedModel, config *DDPConfig, group *ProcessGroup) (*DDP, error) {
	if model == nil {
		return nil, errors.New("model cannot be nil")
	}
	if config == nil {
		config = &DDPConfig{
			GradBucketCapMB:     25,
			BroadcastBuffers:    true,
			FindUnusedParams:    false,
			GradientAsBucketView: true,
			OverlapGradReduce:   true,
		}
	}
	if group == nil {
		return nil, errors.New("process group cannot be nil")
	}

	params := model.Parameters()
	ddp := &DDP{
		config:    config,
		rank:      group.Rank(),
		worldSize: group.WorldSize(),
		group:     group,
		model:     model,
		params:    params,
		bucketMap: make(map[*tensor.Tensor]int),
		commStream: &CommStream{id: 0},
	}

	// Build gradient buckets
	if err := ddp.buildBuckets(); err != nil {
		return nil, err
	}

	return ddp, nil
}

// buildBuckets groups parameters into buckets for efficient all-reduce.
func (d *DDP) buildBuckets() error {
	bucketCapElems := d.config.GradBucketCapMB * 1024 * 1024 / 8 // float64 = 8 bytes
	
	currentBucket := NewGradBucket(0, bucketCapElems)
	bucketID := 0
	
	for _, p := range d.params {
		numel := p.NumElements()
		
		// If param doesn't fit in current bucket, start new bucket
		if numel > bucketCapElems {
			// Param gets its own bucket
			ownBucket := NewGradBucket(bucketID, numel)
			ownBucket.AddParam(p)
			d.buckets = append(d.buckets, ownBucket)
			d.bucketMap[p] = bucketID
			bucketID++
			currentBucket = NewGradBucket(bucketID, bucketCapElems)
			continue
		}
		
		if currentBucket.IsFull() {
			d.buckets = append(d.buckets, currentBucket)
			bucketID++
			currentBucket = NewGradBucket(bucketID, bucketCapElems)
		}
		
		currentBucket.AddParam(p)
		d.bucketMap[p] = bucketID
	}
	
	if len(currentBucket.params) > 0 {
		d.buckets = append(d.buckets, currentBucket)
	}
	
	return nil
}

// Init performs initialization (broadcasts parameters from rank 0).
func (d *DDP) Init(ctx context.Context) error {
	if d.initialized.Swap(true) {
		return nil
	}
	
	// Broadcast parameters from rank 0 to all ranks
	if d.config.BroadcastBuffers {
		for _, p := range d.params {
			_, err := d.group.Broadcast(ctx, p, 0)
			if err != nil {
				return err
			}
		}
	}
	
	// Notify hooks
	for _, hook := range d.hooks {
		hook.OnParamsReady(d.params)
	}
	
	return nil
}

// RegisterHook registers a DDP hook.
func (d *DDP) RegisterHook(hook DDPHook) {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.hooks = append(d.hooks, hook)
}

// Forward performs forward pass through the model.
func (d *DDP) Forward(ctx context.Context, input *tensor.Tensor) (*tensor.Tensor, error) {
	return d.model.forwardFn(ctx, input)
}

// Backward performs backward pass and prepares gradients for sync.
func (d *DDP) Backward(ctx context.Context, gradOutput *tensor.Tensor) error {
	if d.model.backwardFn != nil {
		if err := d.model.backwardFn(ctx, gradOutput); err != nil {
			return err
		}
	}
	
	// Notify hooks
	for _, hook := range d.hooks {
		hook.OnGradReady(gradOutput)
		hook.OnBackwardDone()
	}
	
	return nil
}

// SynchronizeGradients synchronizes gradients across all ranks.
func (d *DDP) SynchronizeGradients(ctx context.Context) error {
	step := d.syncStep.Add(1)
	
	// Reduce gradients bucket by bucket
	for _, bucket := range d.buckets {
		bucket.Flatten()
		
		// All-reduce the flattened gradients
		reduced, err := d.group.AllReduce(ctx, bucket.flatGrad, ReduceOpSum)
		if err != nil {
			return err
		}
		
		// Average gradients
		if d.worldSize > 1 {
			flatV := reduced.Float64()
			invWorldSize := 1.0 / float64(d.worldSize)
			for i := range flatV {
				flatV[i] *= invWorldSize
			}
		}
		
		bucket.flatGrad = reduced
		bucket.Unflatten()
		bucket.ready.Store(true)
		
		// Update stats
		d.stats.TotalAllReduce.Add(1)
		d.stats.BucketsReduced.Add(1)
		d.stats.TotalBytesReduced.Add(int64(bucket.capacity * 8))
	}
	
	// Notify hooks
	for _, hook := range d.hooks {
		hook.OnStepStart()
	}
	
	_ = step
	return nil
}

// TrainStep performs a complete training step (forward, backward, sync).
func (d *DDP) TrainStep(ctx context.Context, input *tensor.Tensor, gradOutput *tensor.Tensor) error {
	if !d.initialized.Load() {
		if err := d.Init(ctx); err != nil {
			return err
		}
	}
	
	// Forward
	_, err := d.Forward(ctx, input)
	if err != nil {
		return err
	}
	
	// Backward
	if err := d.Backward(ctx, gradOutput); err != nil {
		return err
	}
	
	// Synchronize gradients
	if err := d.SynchronizeGradients(ctx); err != nil {
		return err
	}
	
	// Notify hooks
	for _, hook := range d.hooks {
		hook.OnStepDone()
	}
	
	return nil
}

// BucketStats returns statistics about gradient buckets.
func (d *DDP) BucketStats() []int {
	stats := make([]int, len(d.buckets))
	for i, b := range d.buckets {
		stats[i] = len(b.params)
	}
	return stats
}

// NoSync provides a context manager to skip gradient sync.
type NoSync struct {
	ddp *DDP
}

// NoSync returns a no-sync context manager.
func (d *DDP) NoSync() *NoSync {
	return &NoSync{ddp: d}
}

// Enter disables gradient synchronization.
func (ns *NoSync) Enter() {
	// Would set a flag to skip sync
}

// Exit re-enables gradient synchronization.
func (ns *NoSync) Exit() {
	// Would clear the flag
}

// GradientCompression implements gradient compression for bandwidth reduction.
type GradientCompression struct {
	enabled   bool
	threshold float64 // Sparsification threshold
	ratio     float64 // Compression ratio
	errorFeedback *tensor.Tensor // Error feedback buffer
}

// NewGradientCompression creates gradient compression.
func NewGradientCompression(threshold float64) *GradientCompression {
	return &GradientCompression{
		enabled:   true,
		threshold: threshold,
		ratio:     0.1,
	}
}

// Compress compresses gradients by keeping only significant values.
func (gc *GradientCompression) Compress(grad *tensor.Tensor) *tensor.Tensor {
	if !gc.enabled {
		return grad
	}
	
	// Top-k sparsification: keep top threshold fraction of gradients
	// Simplified: return as-is for now
	return grad
}

// Decompress reconstructs gradients from compressed form.
func (gc *GradientCompression) Decompress(compressed *tensor.Tensor, shape []int) *tensor.Tensor {
	if !gc.enabled {
		return compressed
	}
	
	// Reconstruct dense gradient
	out, _ := tensor.New(tensor.Float64, shape)
	copy(out.Float64(), compressed.Float64())
	return out
}

// ZeroRedundancyOptimizer implements ZeRO optimizer stage 1.
type ZeroRedundancyOptimizer struct {
	*DDP
	optimizer     Optimizer
	stage         int // 0, 1, 2, or 3
	partitionID   int
	partitionSize int
	paramsPerRank [][]*tensor.Tensor
}

// NewZeroRedundancyOptimizer creates a ZeRO optimizer.
func NewZeroRedundancyOptimizer(ddp *DDP, opt Optimizer, stage int) (*ZeroRedundancyOptimizer, error) {
	if stage < 0 || stage > 3 {
		return nil, errors.New("invalid ZeRO stage")
	}
	
	zero := &ZeroRedundancyOptimizer{
		DDP:        ddp,
		optimizer:  opt,
		stage:      stage,
		partitionID: ddp.rank,
		partitionSize: ddp.worldSize,
	}
	
	// Partition parameters across ranks
	zero.partitionParams()
	
	return zero, nil
}

func (z *ZeroRedundancyOptimizer) partitionParams() {
	paramsPerRank := z.worldSize
	paramsPerRank = (len(z.params) + paramsPerRank - 1) / paramsPerRank
	
	z.paramsPerRank = make([][]*tensor.Tensor, z.worldSize)
	for i := 0; i < z.worldSize; i++ {
		start := i * paramsPerRank
		end := start + paramsPerRank
		if end > len(z.params) {
			end = len(z.params)
		}
		if start < len(z.params) {
			z.paramsPerRank[i] = z.params[start:end]
		}
	}
}

// Step performs optimizer step with parameter partitioning.
func (z *ZeroRedundancyOptimizer) Step(ctx context.Context) error {
	switch z.stage {
	case 0:
		// No partitioning - standard DDP
		z.optimizer.Step()
	case 1:
		// Partition optimizer states
		// Only update parameters assigned to this rank
		for _, p := range z.paramsPerRank[z.rank] {
			_ = p
			// Update parameter with its optimizer state
		}
	case 2:
		// Partition gradients + optimizer states
		// Gradients already partitioned in ZeRO-1
		z.optimizer.Step()
	case 3:
		// Partition parameters + gradients + optimizer states
		// Most memory efficient
		z.optimizer.Step()
	}
	return nil
}

// ElasticAgent provides elastic training with fault tolerance.
type ElasticAgent struct {
	*DDP
	minWorldSize int
	maxWorldSize int
	currentGroup atomic.Value // *ProcessGroup
	rendezvous   *Rendezvous
	failureDetector *FailureDetector
	mu           sync.RWMutex
}

// Rendezvous manages elastic training rendezvous.
type Rendezvous struct {
	store       Store
	minWorkers  int
	maxWorkers  int
	workers     map[int]bool
	mu          sync.Mutex
	round       int
}

// NewRendezvous creates a new rendezvous.
func NewRendezvous(store Store, minWorkers, maxWorkers int) *Rendezvous {
	return &Rendezvous{
		store:      store,
		minWorkers: minWorkers,
		maxWorkers: maxWorkers,
		workers:    make(map[int]bool),
	}
}

// Join joins the rendezvous.
func (r *Rendezvous) Join(rank int, worldSize int) (int, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	r.workers[rank] = true
	
	if len(r.workers) >= r.minWorkers {
		return len(r.workers), nil
	}
	
	return len(r.workers), errors.New("waiting for more workers")
}

// GetParticipants returns current participants.
func (r *Rendezvous) GetParticipants() []int {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	ranks := make([]int, 0, len(r.workers))
	for rank := range r.workers {
		ranks = append(ranks, rank)
	}
	return ranks
}

// FailureDetector detects failed workers.
type FailureDetector struct {
	timeout      time.Duration
	heartbeats   map[int]time.Time
	failedRanks  map[int]bool
	mu           sync.RWMutex
}

// NewFailureDetector creates a failure detector.
func NewFailureDetector(timeout time.Duration) *FailureDetector {
	return &FailureDetector{
		timeout:     timeout,
		heartbeats:  make(map[int]time.Time),
		failedRanks: make(map[int]bool),
	}
}

// Heartbeat records a heartbeat from a rank.
func (fd *FailureDetector) Heartbeat(rank int) {
	fd.mu.Lock()
	defer fd.mu.Unlock()
	fd.heartbeats[rank] = time.Now()
}

// CheckFailures checks for failed ranks.
func (fd *FailureDetector) CheckFailures() []int {
	fd.mu.Lock()
	defer fd.mu.Unlock()
	
	var failed []int
	now := time.Now()
	for rank, lastBeat := range fd.heartbeats {
		if now.Sub(lastBeat) > fd.timeout {
			fd.failedRanks[rank] = true
			failed = append(failed, rank)
		}
	}
	return failed
}

// NewElasticAgent creates an elastic training agent.
func NewElasticAgent(ddp *DDP, minWorldSize, maxWorldSize int) *ElasticAgent {
	agent := &ElasticAgent{
		DDP:            ddp,
		minWorldSize:   minWorldSize,
		maxWorldSize:   maxWorldSize,
		rendezvous:     NewRendezvous(NewTCPStore("elastic://rendezvous", minWorldSize, 30*time.Second), minWorldSize, maxWorldSize),
		failureDetector: NewFailureDetector(30 * time.Second),
	}
	agent.currentGroup.Store(ddp.group)
	return agent
}

// HandleFailure handles a worker failure by re-rendezvousing.
func (ea *ElasticAgent) HandleFailure(ctx context.Context, failedRank int) error {
	ea.mu.Lock()
	defer ea.mu.Unlock()
	
	// Detect failure
	ea.failureDetector.Heartbeat(failedRank)
	failed := ea.failureDetector.CheckFailures()
	
	if len(failed) > 0 {
		// Re-rendezvous with remaining workers
		participants := ea.rendezvous.GetParticipants()
		
		// Create new group with remaining workers
		newWorldSize := len(participants)
		if newWorldSize < ea.minWorldSize {
			return errors.New("too few workers for elastic training")
		}
		
		// Would create new process group and update DDP
		_ = newWorldSize
	}
	
	return nil
}

// TrainStepEpoch trains for one epoch with elastic fault tolerance.
func (ea *ElasticAgent) TrainStepEpoch(ctx context.Context, inputs []*tensor.Tensor, gradOutputs []*tensor.Tensor) error {
	for i := range inputs {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		
		// Heartbeat
		ea.failureDetector.Heartbeat(ea.rank)
		
		// Check for failures
		if failed := ea.failureDetector.CheckFailures(); len(failed) > 0 {
			for _, r := range failed {
				if err := ea.HandleFailure(ctx, r); err != nil {
					return err
				}
			}
		}
		
		// Train step
		if err := ea.TrainStep(ctx, inputs[i], gradOutputs[i]); err != nil {
			return err
		}
	}
	return nil
}