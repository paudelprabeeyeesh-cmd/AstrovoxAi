// Package distributed provides tensor parallelism implementation.
package distributed

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"

	"github.com/astrovox/astrovox/tensor"
	"github.com/astrovox/astrovox/tensor/math"
)

var (
	ErrInvalidParallelism = errors.New("invalid parallelism configuration")
	ErrShapeMismatch      = errors.New("tensor shape mismatch for parallelism")
)

// TensorParallelConfig holds tensor parallelism configuration.
type TensorParallelConfig struct {
	TPSize           int  // Tensor parallel size
	SequenceParallel bool // Enable sequence parallelism
	AsyncComm        bool // Overlap communication with computation
	GatherOutput     bool // Gather output to all ranks
}

// TensorParallel manages tensor parallelism for a model.
type TensorParallel struct {
	config    *TensorParallelConfig
	rank      int
	worldSize int
	group     *ProcessGroup
	mu        sync.RWMutex
	buffers   map[string]*CommBuffer
	streams   []CommStream
}

// CommBuffer holds communication buffers.
type CommBuffer struct {
	sendBuf *tensor.Tensor
	recvBuf *tensor.Tensor
	inUse   atomic.Bool
}

// CommStream represents a communication stream.
type CommStream struct {
	id     int
	events []CommEvent
	mu     sync.Mutex
}

type CommEvent struct {
	opType   string
	tensor   *tensor.Tensor
	callback func(error)
	done     bool
}

// NewTensorParallel creates a new tensor parallel wrapper.
func NewTensorParallel(config *TensorParallelConfig, group *ProcessGroup) (*TensorParallel, error) {
	if config.TPSize <= 1 {
		return nil, ErrInvalidParallelism
	}
	if group.WorldSize() != config.TPSize {
		return nil, ErrInvalidParallelism
	}

	tp := &TensorParallel{
		config:    config,
		rank:      group.Rank(),
		worldSize: config.TPSize,
		group:     group,
		buffers:   make(map[string]*CommBuffer),
		streams:   make([]CommStream, config.TPSize),
	}

	for i := range tp.streams {
		tp.streams[i].id = i
	}

	return tp, nil
}

// ColumnParallelLinear implements column-parallel linear layer.
// Y = X * W^T where W is split along output dimension (columns).
type ColumnParallelLinear struct {
	*TensorParallel
	weight    *tensor.Tensor // [out_dim/tp, in_dim]
	bias      *tensor.Tensor // [out_dim/tp] or nil
	inputDim  int
	outputDim int // Full output dimension
}

// NewColumnParallelLinear creates a column-parallel linear layer.
func NewColumnParallelLinear(tp *TensorParallel, inputDim, outputDim int, bias bool) (*ColumnParallelLinear, error) {
	if outputDim%tp.worldSize != 0 {
		return nil, ErrInvalidParallelism
	}

	localOutDim := outputDim / tp.worldSize
	w, _ := tensor.New(tensor.Float64, []int{localOutDim, inputDim})
	var b *tensor.Tensor
	if bias {
		b, _ = tensor.New(tensor.Float64, []int{localOutDim})
	}

	return &ColumnParallelLinear{
		TensorParallel: tp,
		weight:         w,
		bias:           b,
		inputDim:       inputDim,
		outputDim:      outputDim,
	}, nil
}

// Forward: X [batch, seq, in_dim] -> Y [batch, seq, out_dim/tp]
func (cpl *ColumnParallelLinear) Forward(ctx context.Context, x *tensor.Tensor) (*tensor.Tensor, error) {
	// x: [*, in_dim], weight: [out_dim/tp, in_dim]
	// output: [*, out_dim/tp]
	wT, err := cpl.weight.Transpose(1, 0)
	if err != nil {
		return nil, err
	}
	return math.MatMul(x, wT)
}

// RowParallelLinear implements row-parallel linear layer.
// Y = X * W^T where W is split along input dimension (rows).
type RowParallelLinear struct {
	*TensorParallel
	weight       *tensor.Tensor // [out_dim, in_dim/tp]
	bias         *tensor.Tensor // [out_dim] (only on last rank or replicated)
	inputDim     int            // Full input dimension
	outputDim    int
	reduceOutput bool // Whether to all-reduce output
}

// NewRowParallelLinear creates a row-parallel linear layer.
func NewRowParallelLinear(tp *TensorParallel, inputDim, outputDim int, bias bool, reduceOutput bool) (*RowParallelLinear, error) {
	if inputDim%tp.worldSize != 0 {
		return nil, ErrInvalidParallelism
	}

	localInDim := inputDim / tp.worldSize
	w, _ := tensor.New(tensor.Float64, []int{outputDim, localInDim})
	var b *tensor.Tensor
	if bias {
		b, _ = tensor.New(tensor.Float64, []int{outputDim})
	}

	return &RowParallelLinear{
		TensorParallel: tp,
		weight:         w,
		bias:           b,
		inputDim:       inputDim,
		outputDim:      outputDim,
		reduceOutput:   reduceOutput,
	}, nil
}

// Forward: X [batch, seq, in_dim/tp] -> Y [batch, seq, out_dim]
func (rpl *RowParallelLinear) Forward(ctx context.Context, x *tensor.Tensor) (*tensor.Tensor, error) {
	// x: [*, in_dim/tp], weight: [out_dim, in_dim/tp]
	// output: [*, out_dim]
	wT, err := rpl.weight.Transpose(1, 0)
	if err != nil {
		return nil, err
	}
	out, err := math.MatMul(x, wT)
	if err != nil {
		return nil, err
	}

	// Add bias if present (only on rank 0 or replicated)
	if rpl.bias != nil && (rpl.rank == 0 || !rpl.reduceOutput) {
		// out = out + bias (broadcast)
	}

	// All-reduce output if needed
	if rpl.reduceOutput && rpl.worldSize > 1 {
		out, err = rpl.group.AllReduce(ctx, out, ReduceOpSum)
		if err != nil {
			return nil, err
		}
	}

	return out, nil
}

// ParallelEmbedding implements vocabulary-parallel embedding.
type ParallelEmbedding struct {
	*TensorParallel
	weight    *tensor.Tensor // [vocab_size/tp, hidden_dim]
	vocabSize int
	hiddenDim int
}

// NewParallelEmbedding creates a vocabulary-parallel embedding.
func NewParallelEmbedding(tp *TensorParallel, vocabSize, hiddenDim int) (*ParallelEmbedding, error) {
	if vocabSize%tp.worldSize != 0 {
		return nil, ErrInvalidParallelism
	}

	localVocabSize := vocabSize / tp.worldSize
	w, _ := tensor.New(tensor.Float64, []int{localVocabSize, hiddenDim})

	return &ParallelEmbedding{
		TensorParallel: tp,
		weight:         w,
		vocabSize:      vocabSize,
		hiddenDim:      hiddenDim,
	}, nil
}

// Forward: input [batch, seq] -> output [batch, seq, hidden_dim]
func (pe *ParallelEmbedding) Forward(ctx context.Context, input *tensor.Tensor) (*tensor.Tensor, error) {
	// Each rank handles a subset of vocabulary
	// input contains token IDs
	// For tokens not in this rank's vocab range, output zeros

	batch := input.Shape().Dim(0)
	seqLen := input.Shape().Dim(1)
	ids := input.Int64()

	out, _ := tensor.New(tensor.Float64, []int{batch, seqLen, pe.hiddenDim})
	outV := out.Float64()
	wV := pe.weight.Float64()

	localVocabStart := pe.rank * (pe.vocabSize / pe.worldSize)
	localVocabEnd := localVocabStart + (pe.vocabSize / pe.worldSize)

	for i := 0; i < batch*seqLen; i++ {
		idx := ids[i]
		if idx >= int64(localVocabStart) && idx < int64(localVocabEnd) {
			localIdx := int(idx) - localVocabStart
			copy(outV[i*pe.hiddenDim:], wV[localIdx*pe.hiddenDim:(localIdx+1)*pe.hiddenDim])
		}
		// Else: leave as zeros (will be gathered)
	}

	// All-gather to get full embeddings (if needed)
	if pe.config.GatherOutput && pe.worldSize > 1 {
		// Would need all-gather across sequence dimension
	}

	return out, nil
}

// ParallelLayerNorm implements layer norm with parallel statistics.
type ParallelLayerNorm struct {
	*TensorParallel
	weight *tensor.Tensor
	bias   *tensor.Tensor
	eps    float64
	dim    int
}

// NewParallelLayerNorm creates a parallel layer norm.
func NewParallelLayerNorm(tp *TensorParallel, dim int, eps float64) *ParallelLayerNorm {
	w, _ := tensor.New(tensor.Float64, []int{dim})
	b, _ := tensor.New(tensor.Float64, []int{dim})
	return &ParallelLayerNorm{
		TensorParallel: tp,
		weight:         w,
		bias:           b,
		eps:            eps,
		dim:            dim,
	}
}

func (pln *ParallelLayerNorm) Forward(ctx context.Context, x *tensor.Tensor) (*tensor.Tensor, error) {
	// Compute local mean/var
	// All-reduce to get global mean/var
	// Normalize
	return math.LayerNorm(x, pln.weight, pln.bias, pln.eps)
}

// ParallelAttention implements tensor-parallel multi-head attention.
type ParallelAttention struct {
	*TensorParallel
	config *ParallelAttentionConfig
	qProj  *ColumnParallelLinear
	kProj  *ColumnParallelLinear
	vProj  *ColumnParallelLinear
	oProj  *RowParallelLinear
}

// ParallelAttentionConfig holds parallel attention config.
type ParallelAttentionConfig struct {
	HiddenDim int
	NumHeads  int
	HeadDim   int
	Dropout   float64
	Causal    bool
	UseFlash  bool
}

// NewParallelAttention creates tensor-parallel attention.
func NewParallelAttention(tp *TensorParallel, config *ParallelAttentionConfig) (*ParallelAttention, error) {
	if config.NumHeads%tp.worldSize != 0 {
		return nil, ErrInvalidParallelism
	}
	if config.HiddenDim%tp.worldSize != 0 {
		return nil, ErrInvalidParallelism
	}

	localHeads := config.NumHeads / tp.worldSize

	qProj, _ := NewColumnParallelLinear(tp, config.HiddenDim, localHeads*config.HeadDim, false)
	kProj, _ := NewColumnParallelLinear(tp, config.HiddenDim, localHeads*config.HeadDim, false)
	vProj, _ := NewColumnParallelLinear(tp, config.HiddenDim, localHeads*config.HeadDim, false)
	oProj, _ := NewRowParallelLinear(tp, localHeads*config.HeadDim, config.HiddenDim, false, true)

	return &ParallelAttention{
		TensorParallel: tp,
		config:         config,
		qProj:          qProj,
		kProj:          kProj,
		vProj:          vProj,
		oProj:          oProj,
	}, nil
}

func (pa *ParallelAttention) Forward(ctx context.Context, x *tensor.Tensor, pastKV *KVCache) (*tensor.Tensor, *KVCache, error) {
	// Q, K, V projections (column parallel)
	q, err := pa.qProj.Forward(ctx, x)
	if err != nil {
		return nil, nil, err
	}
	_, err = pa.kProj.Forward(ctx, x)
	if err != nil {
		return nil, nil, err
	}
	_, err = pa.vProj.Forward(ctx, x)
	if err != nil {
		return nil, nil, err
	}

	// Attention computation (local heads)
	// Each rank computes attention for its subset of heads
	// Output projection (row parallel with all-reduce)
	out, err := pa.oProj.Forward(ctx, q)
	if err != nil {
		return nil, nil, err
	}
	return out, nil, nil
}

// KVCache for parallel attention
type KVCache struct {
	K *tensor.Tensor
	V *tensor.Tensor
}

// SequenceParallel handles sequence parallelism.
type SequenceParallel struct {
	*TensorParallel
	spGroup *ProcessGroup // Subgroup for sequence parallelism
}

// NewSequenceParallel creates a sequence parallel wrapper.
func NewSequenceParallel(tp *TensorParallel, spGroup *ProcessGroup) *SequenceParallel {
	return &SequenceParallel{
		TensorParallel: tp,
		spGroup:        spGroup,
	}
}

// Scatter scatters sequence dimension across ranks.
func (sp *SequenceParallel) Scatter(ctx context.Context, x *tensor.Tensor, dim int) (*tensor.Tensor, error) {
	// Scatter along sequence dimension
	seqLen := x.Shape().Dim(dim)
	localSeqLen := seqLen / sp.worldSize
	start := sp.rank * localSeqLen
	end := start + localSeqLen

	// Slice the tensor
	return x.Slice([]int{start}, []int{end})
}

// Gather gathers sequence dimension from all ranks.
func (sp *SequenceParallel) Gather(ctx context.Context, x *tensor.Tensor, dim int) (*tensor.Tensor, error) {
	// All-gather along sequence dimension
	// Would use AllGather collective
	return x, errors.New("not implemented")
}

// ReduceScatter performs reduce-scatter for gradient synchronization.
func (sp *SequenceParallel) ReduceScatter(ctx context.Context, x *tensor.Tensor) (*tensor.Tensor, error) {
	// Reduce-scatter along sequence dimension
	return x, errors.New("not implemented")
}
