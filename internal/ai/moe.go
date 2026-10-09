// Package ai provides Mixture of Experts (MoE) implementation.
package ai

import (
	"math"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/tensor"
	"github.com/astrovox/astrovox/tensor/math"
)

// MoEConfig holds configuration for Mixture of Experts.
type MoEConfig struct {
	NumExperts      int
	TopK            int
	HiddenDim       int
	ExpertDim       int
	CapacityFactor  float64 // Capacity multiplier for expert capacity
	Dropout         float64
	RouterType      RouterType
	AuxLossCoeff    float64
	ZLossCoeff      float64
	UseGroupedGemm  bool
}

// RouterType defines the routing strategy.
type RouterType int

const (
	RouterTopK RouterType = iota
	RouterTopP
	RouterExpertChoice
	RouterRandom
)

// DefaultMoEConfig returns a default MoE configuration.
func DefaultMoEConfig() *MoEConfig {
	return &MoEConfig{
		NumExperts:     8,
		TopK:           2,
		HiddenDim:      768,
		ExpertDim:      3072,
		CapacityFactor: 1.25,
		Dropout:        0.1,
		RouterType:     RouterTopK,
		AuxLossCoeff:   0.01,
		ZLossCoeff:     0.001,
	}
}

// MoELayer implements a Mixture of Experts layer.
type MoELayer struct {
	config      *MoEConfig
	experts     []*Expert
	router      *Router
	dropout     float64
	training    bool
}

// Expert is a single expert network (typically an MLP).
type Expert struct {
	fc1    *Linear
	fc2    *Linear
	act    ActivationType
	dropout float64
}

func NewExpert(config *MoEConfig) *Expert {
	return &Expert{
		fc1:    NewLinear(config.HiddenDim, config.ExpertDim, true),
		fc2:    NewLinear(config.ExpertDim, config.HiddenDim, true),
		act:    ActGELU,
		dropout: config.Dropout,
	}
}

func (e *Expert) Forward(x *tensor.Tensor) (*tensor.Tensor, error) {
	x, err := e.fc1.Forward(x)
	if err != nil {
		return nil, err
	}
	x, err = math.FusedActApply(x, e.act, 1, 0)
	if err != nil {
		return nil, err
	}
	if e.dropout > 0 {
		// x = dropout(x)
	}
	return e.fc2.Forward(x)
}

// Router computes expert assignments for tokens.
type Router struct {
	config       *MoEConfig
	weight       *tensor.Tensor // [num_experts, hidden_dim]
	bias         *tensor.Tensor // [num_experts]
	noiseScale   float64
}

func NewRouter(config *MoEConfig) *Router {
	w, _ := tensor.New(tensor.Float64, []int{config.NumExperts, config.HiddenDim})
	b, _ := tensor.New(tensor.Float64, []int{config.NumExperts})
	return &Router{
		config:  config,
		weight:  w,
		bias:    b,
		noiseScale: 1.0,
	}
}

// Route computes expert assignments.
// input: [batch*seq_len, hidden_dim] or [batch, seq_len, hidden_dim]
// Returns: (expert_indices, expert_weights, router_logits)
func (r *Router) Route(input *tensor.Tensor) ([][]int, [][]float64, *tensor.Tensor, error) {
	// Flatten input to [tokens, hidden_dim]
	origShape := input.Shape().Dims()
	tokens := 1
	for _, d := range origShape[:len(origShape)-1] {
		tokens *= d
	}
	hiddenDim := origShape[len(origShape)-1]

	flat, err := input.Reshape(tokens, hiddenDim)
	if err != nil {
		return nil, nil, nil, err
	}

	// Compute router logits: [tokens, num_experts]
	// logits = input @ weight^T + bias
	logits, err := math.MatMul(flat, r.weight.Transpose())
	if err != nil {
		return nil, nil, nil, err
	}

	// Add bias
	if r.bias != nil {
		logitsV := logits.Float64()
		biasV := r.bias.Float64()
		numExperts := r.config.NumExperts
		for i := 0; i < tokens; i++ {
			for j := 0; j < numExperts; j++ {
				logitsV[i*numExperts+j] += biasV[j]
			}
		}
	}

	// Add noise during training for exploration
	if r.noiseScale > 0 && r.training {
		// Add Gaussian noise
		// noise ~ N(0, noiseScale)
		// logits += noise
	}

	// Select top-k experts per token
	expertIndices, expertWeights := r.selectTopK(logits, r.config.TopK)

	return expertIndices, expertWeights, logits, nil
}

func (r *Router) selectTopK(logits *tensor.Tensor, k int) ([][]int, [][]float64) {
	tokens := logits.Shape().Dim(0)
	numExperts := logits.Shape().Dim(1)
	logitsV := logits.Float64()

	expertIndices := make([][]int, tokens)
	expertWeights := make([][]float64, tokens)

	for i := 0; i < tokens; i++ {
		// Find top-k
		type kv struct {
			idx int
			val float64
		}
		pairs := make([]kv, numExperts)
		for j := 0; j < numExperts; j++ {
			pairs[j] = kv{j, logitsV[i*numExperts+j]}
		}

		// Partial sort for top-k
		for j := 0; j < k && j < numExperts; j++ {
			maxIdx := j
			for l := j + 1; l < numExperts; l++ {
				if pairs[l].val > pairs[maxIdx].val {
					maxIdx = l
				}
			}
			pairs[j], pairs[maxIdx] = pairs[maxIdx], pairs[j]
		}

		// Softmax over top-k
		topKVals := make([]float64, k)
		for j := 0; j < k; j++ {
			topKVals[j] = pairs[j].val
		}
		// Softmax
		maxVal := topKVals[0]
		for j := 1; j < k; j++ {
			if topKVals[j] > maxVal {
				maxVal = topKVals[j]
			}
		}
		sum := 0.0
		for j := 0; j < k; j++ {
			topKVals[j] = math.Exp(topKVals[j] - maxVal)
			sum += topKVals[j]
		}
		for j := 0; j < k; j++ {
			topKVals[j] /= sum
		}

		expertIndices[i] = make([]int, k)
		expertWeights[i] = make([]float64, k)
		for j := 0; j < k; j++ {
			expertIndices[i][j] = pairs[j].idx
			expertWeights[i][j] = topKVals[j]
		}
	}

	return expertIndices, expertWeights
}

// Forward implements the MoE forward pass.
// input: [batch, seq_len, hidden_dim]
// Returns: output, router_logits, aux_loss
func (m *MoELayer) Forward(input *tensor.Tensor) (*tensor.Tensor, *tensor.Tensor, float64, error) {
	if input == nil {
		return nil, nil, 0, errors.New(errors.CodeInvalidArgument, "nil input")
	}

	batch := input.Shape().Dim(0)
	seqLen := input.Shape().Dim(1)
	hiddenDim := input.Shape().Dim(2)
	tokens := batch * seqLen

	// Flatten to [tokens, hidden_dim]
	flat, err := input.Reshape(tokens, hiddenDim)
	if err != nil {
		return nil, nil, 0, err
	}

	// Route tokens to experts
	expertIndices, expertWeights, routerLogits, err := m.router.Route(flat)
	if err != nil {
		return nil, nil, 0, err
	}

	// Compute expert capacity
	capacity := int(float64(tokens) * m.config.CapacityFactor / float64(m.config.NumExperts))
	if capacity < 1 {
		capacity = 1
	}

	// Dispatch tokens to experts
	// For each expert, gather assigned tokens
	expertInputs := make([]*tensor.Tensor, m.config.NumExperts)
	expertTokenIdx := make([][]int, m.config.NumExperts)
	expertTokenWeights := make([][]float64, m.config.NumExperts)

	for e := 0; e < m.config.NumExperts; e++ {
		expertInputs[e] = nil
		expertTokenIdx[e] = []int{}
		expertTokenWeights[e] = []float64{}
	}

	for t := 0; t < tokens; t++ {
		for k := 0; k < m.config.TopK; k++ {
			e := expertIndices[t][k]
			w := expertWeights[t][k]
			if len(expertTokenIdx[e]) < capacity {
				expertTokenIdx[e] = append(expertTokenIdx[e], t)
				expertTokenWeights[e] = append(expertTokenWeights[e], w)
			}
		}
	}

	// Process each expert
	expertOutputs := make([]*tensor.Tensor, m.config.NumExperts)
	for e := 0; e < m.config.NumExperts; e++ {
		if len(expertTokenIdx[e]) == 0 {
			continue
		}

		// Gather tokens for this expert
		expertIn := tensor.Must(tensor.New(tensor.Float64, []int{len(expertTokenIdx[e]), hiddenDim}))
		inV := expertIn.Float64()
		flatV := flat.Float64()
		for i, idx := range expertTokenIdx[e] {
			copy(inV[i*hiddenDim:], flatV[idx*hiddenDim:(idx+1)*hiddenDim])
		}

		// Expert forward
		out, err := m.experts[e].Forward(expertIn)
		if err != nil {
			return nil, nil, 0, err
		}
		expertOutputs[e] = out
	}

	// Combine expert outputs
	// output = sum_k weight_k * expert_k(tokens_k)
	output := tensor.Must(tensor.New(tensor.Float64, []int{tokens, hiddenDim}))
	outV := output.Float64()

	for e := 0; e < m.config.NumExperts; e++ {
		if expertOutputs[e] == nil {
			continue
		}
		outV_e := expertOutputs[e].Float64()
		for i, idx := range expertTokenIdx[e] {
			w := expertTokenWeights[e][i]
			for d := 0; d < hiddenDim; d++ {
				outV[idx*hiddenDim+d] += w * outV_e[i*hiddenDim+d]
			}
		}
	}

	// Reshape back
	output, err = output.Reshape(append(origShape[:len(origShape)-1], hiddenDim)...)
	if err != nil {
		return nil, nil, 0, err
	}

	// Compute auxiliary losses
	auxLoss := m.computeAuxLoss(routerLogits, expertTokenIdx, tokens)

	return output, routerLogits, auxLoss, nil
}

func (m *MoELayer) computeAuxLoss(logits *tensor.Tensor, expertTokenIdx [][]int, tokens int) float64 {
	if m.config.AuxLossCoeff == 0 {
		return 0
	}

	numExperts := m.config.NumExperts
	logitsV := logits.Float64()

	// Compute fraction of tokens routed to each expert
	// f_i = count_i / tokens
	// P_i = mean(softmax(logits)[:, i])
	// aux_loss = sum_i f_i * P_i * num_experts

	softmax := make([][]float64, tokens)
	for i := 0; i < tokens; i++ {
		softmax[i] = make([]float64, numExperts)
		// Softmax over experts
		maxVal := logitsV[i*numExperts]
		for j := 1; j < numExperts; j++ {
			if logitsV[i*numExperts+j] > maxVal {
				maxVal = logitsV[i*numExperts+j]
			}
		}
		sum := 0.0
		for j := 0; j < numExperts; j++ {
			softmax[i][j] = math.Exp(logitsV[i*numExperts+j] - maxVal)
			sum += softmax[i][j]
		}
		for j := 0; j < numExperts; j++ {
			softmax[i][j] /= sum
		}
	}

	// Mean probability per expert
	P := make([]float64, numExperts)
	for j := 0; j < numExperts; j++ {
		for i := 0; i < tokens; i++ {
			P[j] += softmax[i][j]
		}
		P[j] /= float64(tokens)
	}

	// Fraction of tokens per expert
	f := make([]float64, numExperts)
	for j := 0; j < numExperts; j++ {
		f[j] = float64(len(expertTokenIdx[j])) / float64(tokens)
	}

	// Auxiliary loss
	auxLoss := 0.0
	for j := 0; j < numExperts; j++ {
		auxLoss += f[j] * P[j]
	}
	auxLoss *= float64(numExperts)

	return auxLoss * m.config.AuxLossCoeff
}

// NewMoELayer creates a new MoE layer.
func NewMoELayer(config *MoEConfig) *MoELayer {
	if config == nil {
		config = DefaultMoEConfig()
	}

	experts := make([]*Expert, config.NumExperts)
	for i := 0; i < config.NumExperts; i++ {
		experts[i] = NewExpert(config)
	}

	return &MoELayer{
		config:  config,
		experts: experts,
		router:  NewRouter(config),
		dropout: config.Dropout,
		training: true,
	}
}

// SetTraining sets training mode.
func (m *MoELayer) SetTraining(training bool) {
	m.training = training
	m.router.training = training
	for _, e := range m.experts {
		// Experts don't have separate training flag
	}
}

// ExpertChoiceRouter implements expert-choice routing (each expert chooses tokens).
type ExpertChoiceRouter struct {
	config     *MoEConfig
	expertCap  int // Tokens per expert
}

func NewExpertChoiceRouter(config *MoEConfig) *ExpertChoiceRouter {
	return &ExpertChoiceRouter{
		config:    config,
		expertCap: int(config.CapacityFactor * float64(config.HiddenDim) / float64(config.NumExperts)),
	}
}

func (ecr *ExpertChoiceRouter) Route(input *tensor.Tensor, expertWeights *tensor.Tensor) ([][]int, [][]float64, error) {
	// Expert-choice: each expert selects top tokens
	// Not fully implemented
	return nil, nil, errors.New(errors.CodeUnimplemented, "expert-choice router not implemented")
}

// SwitchTransformerMoE implements the Switch Transformer MoE variant.
type SwitchTransformerMoE struct {
	*MoELayer
}

func NewSwitchTransformerMoE(config *MoEConfig) *SwitchTransformerMoE {
	// Switch Transformer uses top-1 routing
	config.TopK = 1
	return &SwitchTransformerMoE{MoELayer: NewMoELayer(config)}
}

// SparseMoE implements a sparse MoE with expert parallelism support.
type SparseMoE struct {
	*MoELayer
	expertParallelism int
}

func NewSparseMoE(config *MoEConfig, expertParallelism int) *SparseMoE {
	return &SparseMoE{
		MoELayer:        NewMoELayer(config),
		expertParallelism: expertParallelism,
	}
}

// MoEStats tracks MoE routing statistics.
type MoEStats struct {
	TokensPerExpert    []int
	ExpertUtilization  []float64
	LoadBalanceLoss    float64
	RouterEntropy      float64
}

func (m *MoELayer) GetStats() MoEStats {
	tokens := 0
	for _, idxs := range m.router.expertTokenIdx {
		tokens += len(idxs)
	}

	stats := MoEStats{
		TokensPerExpert:   make([]int, m.config.NumExperts),
		ExpertUtilization: make([]float64, m.config.NumExperts),
	}

	for e := 0; e < m.config.NumExperts; e++ {
		stats.TokensPerExpert[e] = len(m.router.expertTokenIdx[e])
		if tokens > 0 {
			stats.ExpertUtilization[e] = float64(stats.TokensPerExpert[e]) / float64(tokens)
		}
	}

	return stats
}

// Add missing fields to Router
func init() {
	// This will be added via composition in actual implementation
}