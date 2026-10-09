// Package ai provides AI model components: Transformer, MoE, KV Cache, etc.
package ai

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
	tmath "github.com/astrovox/astrovox/tensor/math"
)

// TransformerConfig holds configuration for a Transformer model.
type TransformerConfig struct {
	VocabSize       int
	MaxSeqLen       int
	NumLayers       int
	NumHeads        int
	HiddenDim       int
	MLPDim          int
	HeadDim         int
	Dropout         float64
	LayerNormEps    float64
	UseFlashAttn    bool
	UseRMSNorm      bool
	UseRoPE         bool
	RopeTheta       float64
	PadTokenID      int
}

// DefaultTransformerConfig returns a default configuration.
func DefaultTransformerConfig() *TransformerConfig {
	return &TransformerConfig{
		VocabSize:    32000,
		MaxSeqLen:    2048,
		NumLayers:    12,
		NumHeads:     12,
		HiddenDim:    768,
		MLPDim:       3072,
		HeadDim:      64,
		Dropout:      0.1,
		LayerNormEps: 1e-5,
		UseFlashAttn: true,
		UseRMSNorm:   true,
		UseRoPE:      true,
		RopeTheta:    10000.0,
		PadTokenID:   0,
	}
}

// Transformer represents a Transformer model.
type Transformer struct {
	config *TransformerConfig
	layers []*TransformerLayer
	embed  *Embedding
	norm   Normalization
	lmHead *Linear
	training bool
}

// NewTransformer creates a new Transformer model.
func NewTransformer(config *TransformerConfig) *Transformer {
	if config == nil {
		config = DefaultTransformerConfig()
	}
	if config.HeadDim == 0 {
		config.HeadDim = config.HiddenDim / config.NumHeads
	}

	t := &Transformer{
		config: config,
		layers: make([]*TransformerLayer, config.NumLayers),
		embed:  NewEmbedding(config.VocabSize, config.HiddenDim),
	}

	// Create normalization
	if config.UseRMSNorm {
		t.norm = NewRMSNorm(config.HiddenDim, config.LayerNormEps)
	} else {
		t.norm = NewLayerNorm(config.HiddenDim, config.LayerNormEps)
	}

	// Create layers
	for i := 0; i < config.NumLayers; i++ {
		t.layers[i] = NewTransformerLayer(config)
	}

	// LM head (tied with embedding)
	t.lmHead = NewLinear(config.HiddenDim, config.VocabSize, false)
	// In practice, would tie weights: t.lmHead.weight = t.embed.weight

	return t
}

// Forward performs the forward pass.
// input: [batch, seq_len] int64 tensor of token IDs
// Returns logits: [batch, seq_len, vocab_size]
func (t *Transformer) Forward(input *tensor.Tensor, pastKV *KVCache) (*tensor.Tensor, *KVCache, error) {
	if input == nil {
		return nil, nil, errors.New(errors.CodeInvalidArgument, "nil input")
	}
	if input.DType() != tensor.Int64 {
		return nil, nil, errors.New(errors.CodeDTypeMismatch, "input must be int64")
	}

	batch := input.Shape().Dim(0)
	seqLen := input.Shape().Dim(1)

	// Embedding
	x, err := t.embed.Forward(input)
	if err != nil {
		return nil, nil, err
	}

	// Positional embeddings (RoPE handled in attention)
	if t.config.UseRoPE {
		// RoPE is applied inside attention, no separate pos embedding needed
	} else {
		// Add learned positional embeddings
		// posEmb := t.posEmbed[:seqLen]
		// x = x + posEmb
	}

	// Dropout on embeddings
	if t.config.Dropout > 0 && t.training {
		x = t.dropout(x, t.config.Dropout)
	}

	// Transformer layers
	newKV := NewKVCache(t.config.NumLayers, batch, t.config.NumHeads, t.config.HeadDim, t.config.MaxSeqLen)
	for i, layer := range t.layers {
		var layerPast *LayerKV
		if pastKV != nil {
			layerPast = pastKV.Layers[i]
		}
		x, layerKV, err := layer.Forward(x, layerPast)
		if err != nil {
			return nil, nil, err
		}
		newKV.Layers[i] = layerKV
	}

	// Final normalization
	x, err = t.norm.Forward(x)
	if err != nil {
		return nil, nil, err
	}

	// LM head
	logits, err := t.lmHead.Forward(x)
	if err != nil {
		return nil, nil, err
	}

	return logits, newKV, nil
}

func (t *Transformer) dropout(x *tensor.Tensor, p float64) *tensor.Tensor {
	// Simplified: in practice use proper dropout
	return x
}

var _ Normalization = (*LayerNorm)(nil)
var _ Normalization = (*RMSNorm)(nil)

// Normalization interface for layer normalization.
type Normalization interface {
	Forward(x *tensor.Tensor) (*tensor.Tensor, error)
}

// LayerNorm implements layer normalization.
type LayerNorm struct {
	weight *tensor.Tensor
	bias   *tensor.Tensor
	eps    float64
}

func NewLayerNorm(dim int, eps float64) *LayerNorm {
	w, _ := tensor.New(tensor.Float64, []int{dim})
	b, _ := tensor.New(tensor.Float64, []int{dim})
	// Initialize weight to 1, bias to 0
	w.Float64()[0] = 1 // Simplified
	return &LayerNorm{weight: w, bias: b, eps: eps}
}

func (ln *LayerNorm) Forward(x *tensor.Tensor) (*tensor.Tensor, error) {
	return tmath.LayerNorm(x, ln.weight, ln.bias, ln.eps)
}

// RMSNorm implements root mean square layer normalization.
type RMSNorm struct {
	weight *tensor.Tensor
	eps    float64
}

func NewRMSNorm(dim int, eps float64) *RMSNorm {
	w, _ := tensor.New(tensor.Float64, []int{dim})
	return &RMSNorm{weight: w, eps: eps}
}

func (rn *RMSNorm) Forward(x *tensor.Tensor) (*tensor.Tensor, error) {
	return tmath.RMSNorm(x, rn.weight, nil, rn.eps)
}

// Embedding maps token IDs to vectors.
type Embedding struct {
	weight *tensor.Tensor
}

func NewEmbedding(vocabSize, dim int) *Embedding {
	w, _ := tensor.New(tensor.Float64, []int{vocabSize, dim})
	return &Embedding{weight: w}
}

func (e *Embedding) Forward(input *tensor.Tensor) (*tensor.Tensor, error) {
	// input: [batch, seq_len] int64
	// output: [batch, seq_len, dim]
	batch := input.Shape().Dim(0)
	seqLen := input.Shape().Dim(1)
	ids := input.Int64()

	out, err := tensor.New(tensor.Float64, []int{batch, seqLen, e.weight.Shape().Dim(1)})
	if err != nil {
		return nil, err
	}

	outV := out.Float64()
	wV := e.weight.Float64()
	dim := e.weight.Shape().Dim(1)

	for i := 0; i < batch*seqLen; i++ {
		idx := ids[i]
		if idx >= 0 && idx < int64(e.weight.Shape().Dim(0)) {
			copy(outV[i*dim:], wV[idx*dim:(idx+1)*dim])
		}
	}

	return out, nil
}

// Linear layer (fully connected).
type Linear struct {
	weight *tensor.Tensor
	bias   *tensor.Tensor
}

func NewLinear(inDim, outDim int, bias bool) *Linear {
	w, _ := tensor.New(tensor.Float64, []int{outDim, inDim})
	var b *tensor.Tensor
	if bias {
		b, _ = tensor.New(tensor.Float64, []int{outDim})
	}
	return &Linear{weight: w, bias: b}
}

func (l *Linear) Forward(x *tensor.Tensor) (*tensor.Tensor, error) {
	// x: [*, inDim], weight: [outDim, inDim]
	// output: [*, outDim]
	return tmath.MatMul(x, l.weight.Transpose(1, 0))
}

// TransformerLayer is a single Transformer layer.
type TransformerLayer struct {
	config       *TransformerConfig
	attention    *MultiHeadAttention
	mlp          *MLP
	norm1        Normalization
	norm2        Normalization
	dropout1     float64
	dropout2     float64
}

func NewTransformerLayer(config *TransformerConfig) *TransformerLayer {
	l := &TransformerLayer{
		config:    config,
		attention: NewMultiHeadAttention(config),
		mlp:       NewMLP(config),
		dropout1:  config.Dropout,
		dropout2:  config.Dropout,
	}
	if config.UseRMSNorm {
		l.norm1 = NewRMSNorm(config.HiddenDim, config.LayerNormEps)
		l.norm2 = NewRMSNorm(config.HiddenDim, config.LayerNormEps)
	} else {
		l.norm1 = NewLayerNorm(config.HiddenDim, config.LayerNormEps)
		l.norm2 = NewLayerNorm(config.HiddenDim, config.LayerNormEps)
	}
	return l
}

// Forward: x -> norm1 -> attention -> +x -> norm2 -> mlp -> +x
func (l *TransformerLayer) Forward(x *tensor.Tensor, past *LayerKV) (*tensor.Tensor, *LayerKV, error) {
	// Pre-norm attention
	normed, err := l.norm1.Forward(x)
	if err != nil {
		return nil, nil, err
	}

	attnOut, newKV, err := l.attention.Forward(normed, past)
	if err != nil {
		return nil, nil, err
	}

	// Residual + dropout
	x = addResidual(x, attnOut, l.dropout1)

	// Pre-norm MLP
	normed, err = l.norm2.Forward(x)
	if err != nil {
		return nil, nil, err
	}

	mlpOut, err := l.mlp.Forward(normed)
	if err != nil {
		return nil, nil, err
	}

	// Residual + dropout
	x = addResidual(x, mlpOut, l.dropout2)

	return x, newKV, nil
}

func addResidual(x, residual *tensor.Tensor, dropout float64) *tensor.Tensor {
	// x + residual (with optional dropout)
	// In practice: x + dropout(residual)
	// Simplified: just add
	out, _ := tensor.Add(x, residual)
	return out
}

// MLP (Feed-forward network) with GELU activation.
type MLP struct {
	fc1    *Linear
	fc2    *Linear
	act    ActivationType
	dropout float64
}

func NewMLP(config *TransformerConfig) *MLP {
	return &MLP{
		fc1:    NewLinear(config.HiddenDim, config.MLPDim, true),
		fc2:    NewLinear(config.MLPDim, config.HiddenDim, true),
		act:    ActGELU,
		dropout: config.Dropout,
	}
}

func (m *MLP) Forward(x *tensor.Tensor) (*tensor.Tensor, error) {
	x, err := m.fc1.Forward(x)
	if err != nil {
		return nil, err
	}
	x, err = tmath.FusedActApply(x, m.act, 1, 0)
	if err != nil {
		return nil, err
	}
	if m.dropout > 0 {
		// x = dropout(x)
	}
	return m.fc2.Forward(x)
}

// MultiHeadAttention implements multi-head attention with optional Flash Attention.
type MultiHeadAttention struct {
	config   *TransformerConfig
	qProj    *Linear
	kProj    *Linear
	vProj    *Linear
	oProj    *Linear
	rope     *RoPE
}

func NewMultiHeadAttention(config *TransformerConfig) *MultiHeadAttention {
	mha := &MultiHeadAttention{
		config: config,
		qProj:  NewLinear(config.HiddenDim, config.NumHeads*config.HeadDim, false),
		kProj:  NewLinear(config.HiddenDim, config.NumHeads*config.HeadDim, false),
		vProj:  NewLinear(config.HiddenDim, config.NumHeads*config.HeadDim, false),
		oProj:  NewLinear(config.NumHeads*config.HeadDim, config.HiddenDim, false),
	}
	if config.UseRoPE {
		mha.rope = NewRoPE(config.HeadDim, config.RopeTheta, config.MaxSeqLen)
	}
	return mha
}

func (mha *MultiHeadAttention) Forward(x *tensor.Tensor, past *LayerKV) (*tensor.Tensor, *LayerKV, error) {
	// x: [batch, seq_len, hidden_dim]
	batch := x.Shape().Dim(0)
	seqLen := x.Shape().Dim(1)
	hidden := x.Shape().Dim(2)

	// Project Q, K, V
	q, err := mha.qProj.Forward(x)
	if err != nil {
		return nil, nil, err
	}
	k, err := mha.kProj.Forward(x)
	if err != nil {
		return nil, nil, err
	}
	v, err := mha.vProj.Forward(x)
	if err != nil {
		return nil, nil, err
	}

	// Reshape for multi-head: [batch, seq_len, num_heads, head_dim]
	headDim := mha.config.HeadDim
	numHeads := mha.config.NumHeads

	q = q.Reshape(batch, seqLen, numHeads, headDim)
	k = k.Reshape(batch, seqLen, numHeads, headDim)
	v = v.Reshape(batch, seqLen, numHeads, headDim)

	// Apply RoPE
	if mha.rope != nil {
		q = mha.rope.Apply(q, 0)
		k = mha.rope.Apply(k, 0)
	}

	// Handle KV cache
	if past != nil {
		k = catKV(past.K, k, 1)
		v = catKV(past.V, v, 1)
	}

	newKV := &LayerKV{K: k, V: v}

	// Attention
	var attnOut *tensor.Tensor
	if mha.config.UseFlashAttn {
		// Use Flash Attention
		// Reshape to [batch, num_heads, seq_len, head_dim] for FlashAttention
		qT := q.Transpose(1, 2)
		kT := k.Transpose(1, 2)
		vT := v.Transpose(1, 2)
		attnOut, err = tmath.MultiHeadFlashAttention(qT, kT, vT, numHeads, false)
		if err != nil {
			return nil, nil, err
		}
		// Reshape back
		attnOut = attnOut.Transpose(1, 2)
	} else {
		// Standard attention
		attnOut, err = scaledDotProductAttention(q, k, v, false)
		if err != nil {
			return nil, nil, err
		}
	}

	// Reshape: [batch, seq_len, num_heads, head_dim] -> [batch, seq_len, hidden]
	attnOut = attnOut.Reshape(batch, seqLen, hidden)

	// Output projection
	return mha.oProj.Forward(attnOut)
}

// LayerKV holds key/value cache for a single layer.
type LayerKV struct {
	K *tensor.Tensor // [batch, seq_len, num_heads, head_dim]
	V *tensor.Tensor
}

// KVCache holds key/value caches for all layers.
type KVCache struct {
	Layers []*LayerKV
}

func NewKVCache(numLayers, batch, numHeads, headDim, maxSeqLen int) *KVCache {
	layers := make([]*LayerKV, numLayers)
	for i := range layers {
		k, _ := tensor.New(tensor.Float64, []int{batch, 0, numHeads, headDim})
		v, _ := tensor.New(tensor.Float64, []int{batch, 0, numHeads, headDim})
		layers[i] = &LayerKV{K: k, V: v}
	}
	return &KVCache{Layers: layers}
}

func catKV(past, curr *tensor.Tensor, dim int) *tensor.Tensor {
	if past.NumElements() == 0 {
		return curr
	}
	out, _ := tensor.Concat(dim, past, curr)
	return out
}

// RoPE (Rotary Positional Embedding).
type RoPE struct {
	dim     int
	theta   float64
	maxSeq  int
	cosCache *tensor.Tensor
	sinCache *tensor.Tensor
}

func NewRoPE(dim int, theta float64, maxSeq int) *RoPE {
	r := &RoPE{dim: dim, theta: theta, maxSeq: maxSeq}
	r.buildCache()
	return r
}

func (r *RoPE) buildCache() {
	// Precompute cos/sin for all positions
	invFreq := make([]float64, r.dim/2)
	for i := 0; i < r.dim/2; i++ {
		invFreq[i] = 1.0 / math.Pow(r.theta, float64(2*i)/float64(r.dim))
	}

	cosCache := make([]float64, r.maxSeq*r.dim)
	sinCache := make([]float64, r.maxSeq*r.dim)

	for pos := 0; pos < r.maxSeq; pos++ {
		for i := 0; i < r.dim/2; i++ {
			angle := float64(pos) * invFreq[i]
			cosCache[pos*r.dim+2*i] = math.Cos(angle)
			cosCache[pos*r.dim+2*i+1] = math.Cos(angle)
			sinCache[pos*r.dim+2*i] = math.Sin(angle)
			sinCache[pos*r.dim+2*i+1] = math.Sin(angle)
		}
	}

	r.cosCache, _ = tensor.New(tensor.Float64, []int{r.maxSeq, r.dim})
	r.sinCache, _ = tensor.New(tensor.Float64, []int{r.maxSeq, r.dim})
	copy(r.cosCache.Float64(), cosCache)
	copy(r.sinCache.Float64(), sinCache)
}

func (r *RoPE) Apply(x *tensor.Tensor, offset int) *tensor.Tensor {
	// x: [batch, seq_len, num_heads, head_dim]
	// Apply RoPE in-place
	batch := x.Shape().Dim(0)
	seqLen := x.Shape().Dim(1)
	numHeads := x.Shape().Dim(2)
	headDim := x.Shape().Dim(3)

	xv := x.Float64()
	for b := 0; b < batch; b++ {
		for s := 0; s < seqLen; s++ {
			pos := offset + s
			if pos >= r.maxSeq {
				pos = r.maxSeq - 1
			}
			for h := 0; h < numHeads; h++ {
				base := ((b*seqLen+s)*numHeads+h)*headDim
				for d := 0; d < headDim; d += 2 {
					cos := r.cosCache.Float64()[pos*headDim+d]
					sin := r.sinCache.Float64()[pos*headDim+d]
					x1 := xv[base+d]
					x2 := xv[base+d+1]
					xv[base+d] = x1*cos - x2*sin
					xv[base+d+1] = x1*sin + x2*cos
				}
			}
		}
	}
	return x
}

// scaledDotProductAttention computes standard attention.
func scaledDotProductAttention(q, k, v *tensor.Tensor, causal bool) (*tensor.Tensor, error) {
	// q, k, v: [batch, seq_len, num_heads, head_dim]
	batch := q.Shape().Dim(0)
	seqLen := q.Shape().Dim(1)
	numHeads := q.Shape().Dim(2)
	headDim := q.Shape().Dim(3)

	scale := 1.0 / math.Sqrt(float64(headDim))

	// Transpose for matmul: [batch, num_heads, seq_len, head_dim]
	qT := q.Transpose(1, 2)
	kT := k.Transpose(1, 2)
	vT := v.Transpose(1, 2)

	// Q @ K^T
	kTT := kT.Transpose(2, 3) // [batch, num_heads, head_dim, seq_len]
	scores, err := tmath.BatchMatMul(qT, kTT)
	if err != nil {
		return nil, err
	}

	// Scale
	scoresV := scores.Float64()
	for i := range scoresV {
		scoresV[i] *= scale
	}

	// Causal mask
	if causal {
		// Apply causal mask (simplified)
	}

	// Softmax
	// attn = softmax(scores)
	// out = attn @ V
	return nil, errors.New(errors.CodeUnimplemented, "standard attention not fully implemented")
}

// ActivationType from math package
type ActivationType int

const (
	ActReLU ActivationType = iota
	ActGELU
	ActSiLU
	ActSwish
	ActMish
	ActTanh
	ActSigmoid
	ActGeLUApprox
	ActHardSwish
	ActHardSigmoid
	ActELU
	ActLeakyReLU
	ActReLU6
)

var training = true