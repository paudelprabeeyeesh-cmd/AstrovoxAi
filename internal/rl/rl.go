// Package rl provides reinforcement learning primitives: experience
// replay, epsilon-greedy action selection, DQN and REINFORCE helpers.
package rl

import (
	"errors"
	"math"
)

// RL errors.
var (
	ErrEmptyBuffer   = errors.New("experience buffer is empty")
	ErrInvalidShape  = errors.New("invalid state or action dimension")
)

// Experience is one transition.
type Experience struct {
	State     []float64
	Action    int
	Reward    float64
	NextState []float64
	Done      bool
	Priority  float64
}

// ReplayBuffer stores transitions with uniform or priority sampling.
type ReplayBuffer struct {
	Capacity    int
	experiences []Experience
	position    int
	prioritized bool
}

// NewReplayBuffer creates a replay buffer.
func NewReplayBuffer(capacity int, prioritized bool) (*ReplayBuffer, error) {
	if capacity <= 0 {
		return nil, errors.New("capacity must be positive")
	}
	return &ReplayBuffer{
		Capacity:    capacity,
		experiences: make([]Experience, 0, capacity),
		prioritized: prioritized,
	}, nil
}

// Push adds a transition, evicting the oldest when full.
func (b *ReplayBuffer) Push(e Experience) {
	if len(b.experiences) < b.Capacity {
		b.experiences = append(b.experiences, e)
		return
	}
	b.experiences[b.position] = e
	b.position = (b.position + 1) % b.Capacity
}

// Len returns the number of stored transitions.
func (b *ReplayBuffer) Len() int { return len(b.experiences) }

// Sample returns n transitions. Without priorities, sampling is even.
func (b *ReplayBuffer) Sample(n int, rng *Rng) ([]Experience, error) {
	if len(b.experiences) == 0 {
		return nil, ErrEmptyBuffer
	}
	if n <= 0 {
		return nil, errors.New("sample size must be positive")
	}
	if n > len(b.experiences) {
		n = len(b.experiences)
	}
	if !b.prioritized {
		out := make([]Experience, 0, n)
		for i := 0; i < n; i++ {
			out = append(out, b.experiences[rng.Intn(len(b.experiences))])
		}
		return out, nil
	}
	// Priority sampling proportional to stored priorities.
	weights := make([]float64, len(b.experiences))
	total := 0.0
	for i, e := range b.experiences {
		p := e.Priority
		if p <= 0 {
			p = 1e-6
		}
		weights[i] = p
		total += p
	}
	out := make([]Experience, 0, n)
	for i := 0; i < n; i++ {
		r := rng.Float64() * total
		acc := 0.0
		idx := len(b.experiences) - 1
		for j, w := range weights {
			acc += w
			if r <= acc {
				idx = j
				break
			}
		}
		out = append(out, b.experiences[idx])
	}
	return out, nil
}

// Clear empties the buffer.
func (b *ReplayBuffer) Clear() {
	b.experiences = nil
	b.position = 0
}

// Rng is a deterministic xorshift64 PRNG.
type Rng struct {
	state uint64
}

// NewRng creates a seeded RNG.
func NewRng(seed uint64) *Rng {
	if seed == 0 {
		seed = 0x9E3779B97F4A7C15
	}
	return &Rng{state: seed}
}

// Float64 returns the next value in [0,1).
func (r *Rng) Float64() float64 {
	r.state ^= r.state << 13
	r.state ^= r.state >> 7
	r.state ^= r.state << 17
	return float64(r.state) / float64(math.MaxUint64)
}

// Intn returns a non-negative value in [0,n).
func (r *Rng) Intn(n int) int {
	if n <= 0 {
		return 0
	}
	return int(float64(n) * r.Float64())
}

// EpsilonGreedy picks an action from a Q-value vector.
func EpsilonGreedy(q []float64, epsilon float64, rng *Rng) (int, error) {
	if len(q) == 0 {
		return 0, ErrInvalidShape
	}
	if epsilon < 0 || epsilon > 1 {
		return 0, errors.New("epsilon must be in [0,1]")
	}
	if rng.Float64() < epsilon {
		return rng.Intn(len(q)), nil
	}
	return argmax(q), nil
}

func argmax(v []float64) int {
	best := 0
	for i := 1; i < len(v); i++ {
		if v[i] > v[best] {
			best = i
		}
	}
	return best
}

// Discount returns the discounted return of a reward trajectory.
// Zero-terminated episodes use done=true to cut the tail. gamma must be
// in [0, 1]; values outside that range fall back to 0.99.
func Discount(rewards []float64, gamma float64, dones []bool) []float64 {
	if gamma < 0 || gamma > 1 {
		gamma = 0.99
	}
	returns := make([]float64, len(rewards))
	acc := 0.0
	for i := len(rewards) - 1; i >= 0; i-- {
		if dones != nil && i < len(dones) && dones[i] {
			acc = 0
		}
		acc = rewards[i] + gamma*acc
		returns[i] = acc
	}
	return returns
}

// NormalizeReturns subtracts the mean and divides by (std + eps).
func NormalizeReturns(returns []float64, eps float64) []float64 {
	if len(returns) == 0 {
		return nil
	}
	mean := 0.0
	for _, r := range returns {
		mean += r
	}
	mean /= float64(len(returns))
	variance := 0.0
	for _, r := range returns {
		d := r - mean
		variance += d * d
	}
	variance /= float64(len(returns))
	std := math.Sqrt(variance)
	out := make([]float64, len(returns))
	for i, r := range returns {
		out[i] = (r - mean) / (std + eps)
	}
	return out
}

// TDError computes the temporal-difference error for a transition.
func TDError(exp Experience, qNext []float64, gamma float64, qValue float64) float64 {
	target := exp.Reward
	if !exp.Done {
		best := argmax(qNext)
		if best < len(qNext) {
			target += gamma * qNext[best]
		}
	}
	return target - qValue
}

// LinearQNet is a small linear Q-network: Q(s) = W s + b.
type LinearQNet struct {
	W      [][]float64 // [stateDim][actionDim]
	B      []float64
	stateDim  int
	actionDim int
}

// NewLinearQNet creates a linear Q-network.
func NewLinearQNet(stateDim, actionDim int) (*LinearQNet, error) {
	if stateDim <= 0 || actionDim <= 0 {
		return nil, ErrInvalidShape
	}
	w := make([][]float64, stateDim)
	for i := range w {
		w[i] = make([]float64, actionDim)
	}
	return &LinearQNet{
		W: w, B: make([]float64, actionDim),
		stateDim: stateDim, actionDim: actionDim,
	}, nil
}

// Forward computes Q-values for a state.
func (n *LinearQNet) Forward(state []float64) ([]float64, error) {
	if len(state) != n.stateDim {
		return nil, ErrInvalidShape
	}
	out := append([]float64(nil), n.B...)
	for i, s := range state {
		for a := 0; a < n.actionDim; a++ {
			out[a] += s * n.W[i][a]
		}
	}
	return out, nil
}

// SGDStep applies one gradient step to the weights.
func (n *LinearQNet) SGDStep(state []float64, gradQ []float64, lr float64) error {
	if len(state) != n.stateDim || len(gradQ) != n.actionDim {
		return ErrInvalidShape
	}
	for i, s := range state {
		for a := 0; a < n.actionDim; a++ {
			n.W[i][a] -= lr * gradQ[a] * s
		}
	}
	for a := 0; a < n.actionDim; a++ {
		n.B[a] -= lr * gradQ[a]
	}
	return nil
}

// PolicyGradientAgent holds a softmax policy over discrete actions.
type PolicyGradientAgent struct {
	Weights    [][]float64 // [stateDim][actionDim]
	stateDim   int
	actionDim  int
	lastProbs  []float64
}

// NewPolicyGradientAgent creates a softmax policy agent.
func NewPolicyGradientAgent(stateDim, actionDim int) (*PolicyGradientAgent, error) {
	if stateDim <= 0 || actionDim <= 0 {
		return nil, ErrInvalidShape
	}
	w := make([][]float64, stateDim)
	for i := range w {
		w[i] = make([]float64, actionDim)
	}
	return &PolicyGradientAgent{Weights: w, stateDim: stateDim, actionDim: actionDim}, nil
}

// Probs returns the softmax action distribution for a state.
func (a *PolicyGradientAgent) Probs(state []float64) ([]float64, error) {
	if len(state) != a.stateDim {
		return nil, ErrInvalidShape
	}
	logits := make([]float64, a.actionDim)
	for act := 0; act < a.actionDim; act++ {
		sum := 0.0
		for i, s := range state {
			sum += s * a.Weights[i][act]
		}
		logits[act] = sum
	}
	probs := softmax(logits)
	a.lastProbs = probs
	return probs, nil
}

// Select samples an action from the policy.
func (a *PolicyGradientAgent) Select(state []float64, rng *Rng) (int, error) {
	probs, err := a.Probs(state)
	if err != nil {
		return 0, err
	}
	r := rng.Float64()
	acc := 0.0
	for i, p := range probs {
		acc += p
		if r <= acc {
			return i, nil
		}
	}
	return a.actionDim - 1, nil
}

// Update applies one REINFORCE update using returns normalized externally.
func (a *PolicyGradientAgent) Update(state []float64, action int, advantage, lr float64) error {
	if len(state) != a.stateDim {
		return ErrInvalidShape
	}
	if action < 0 || action >= a.actionDim {
		return ErrInvalidShape
	}
	probs, err := a.Probs(state)
	if err != nil {
		return err
	}
	// Gradient of log pi(a|s) w.r.t. logits: onehot - probs.
	grad := make([]float64, a.actionDim)
	for i := range probs {
		grad[i] = -probs[i]
	}
	grad[action] += 1.0
	for i := 0; i < a.actionDim; i++ {
		g := lr * advantage * grad[i]
		for j, s := range state {
			a.Weights[j][i] += g * s
		}
	}
	return nil
}

func softmax(v []float64) []float64 {
	if len(v) == 0 {
		return nil
	}
	maxV := v[0]
	for _, x := range v {
		if x > maxV {
			maxV = x
		}
	}
	out := make([]float64, len(v))
	sum := 0.0
	for i, x := range v {
		out[i] = math.Exp(x - maxV)
		sum += out[i]
	}
	if sum > 0 {
		for i := range out {
			out[i] /= sum
		}
	}
	return out
}