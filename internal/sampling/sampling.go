// Package sampling provides decoding strategies: greedy, temperature,
// top-k, top-p (nucleus), beam search, and streaming output.
package sampling

import (
	"errors"
	"fmt"
	"math"
	"sort"
	"sync"
)

// Strategy identifies a sampling strategy.
type Strategy int

const (
	Greedy Strategy = iota
	Temperature
	TopK
	TopP
)

func (s Strategy) String() string {
	switch s {
	case Greedy:
		return "greedy"
	case Temperature:
		return "temperature"
	case TopK:
		return "top_k"
	case TopP:
		return "top_p"
	default:
		return "unknown"
	}
}

// Sampler selects the next token from logits.
type Sampler struct {
	Strategy          Strategy
	Temp              float64
	TopK              int
	TopP              float64
	MinP              float64
	RepetitionPenalty float64
	Rand              *Rng
}

// Rng is a small deterministic PRNG (xorshift64).
type Rng struct {
	mu    sync.Mutex
	state uint64
}

// NewRng creates a seeded RNG.
func NewRng(seed uint64) *Rng {
	if seed == 0 {
		seed = 0x9E3779B97F4A7C15
	}
	return &Rng{state: seed}
}

// Float64 returns the next uniform value in [0,1).
func (r *Rng) Float64() float64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.state ^= r.state << 13
	r.state ^= r.state >> 7
	r.state ^= r.state << 17
	return float64(r.state) / float64(math.MaxUint64)
}

// DefaultSampler returns a greedy sampler.
func DefaultSampler() *Sampler {
	return &Sampler{Strategy: Greedy, Temp: 1.0, TopK: 0, TopP: 1.0, Rand: NewRng(42)}
}

// Sample returns the next token id from logits.
func (s *Sampler) Sample(logits []float64, history []int) (int, error) {
	if len(logits) == 0 {
		return 0, errors.New("empty logits")
	}
	if s.Rand == nil {
		s.Rand = NewRng(42)
	}

	// Work on a copy so the caller's logits are never mutated.
	work := make([]float64, len(logits))
	copy(work, logits)
	logits = work

	// Repetition penalty discourages repeats.
	if s.RepetitionPenalty != 0 && s.RepetitionPenalty != 1.0 {
		hist := make(map[int]bool, len(history))
		for _, h := range history {
			hist[h] = true
		}
		for id := range hist {
			if id < 0 || id >= len(logits) {
				continue
			}
			if logits[id] > 0 {
				logits[id] /= s.RepetitionPenalty
			} else {
				logits[id] *= s.RepetitionPenalty
			}
		}
	}

	switch s.Strategy {
	case Greedy:
		return argmax(logits), nil
	case Temperature:
		if s.Temp <= 0 {
			return argmax(logits), nil
		}
		probs := softmax(scale(logits, s.Temp))
		return sampleFrom(probs, s.Rand), nil
	case TopK:
		k := s.TopK
		if k <= 0 || k > len(logits) {
			k = len(logits)
		}
		idxs := topKIndices(logits, k)
		masked := maskTo(logits, idxs, math.Inf(-1))
		probs := softmax(scale(masked, s.temp()))
		return sampleFrom(probs, s.Rand), nil
	case TopP:
		probs := softmax(scale(logits, s.temp()))
		return nucleus(probs, s.TopP, s.Rand)
	default:
		return argmax(logits), nil
	}
}

func (s *Sampler) temp() float64 {
	if s.Temp <= 0 {
		return 1.0
	}
	return s.Temp
}

func scale(v []float64, t float64) []float64 {
	out := make([]float64, len(v))
	for i, x := range v {
		out[i] = x / t
	}
	return out
}

func softmax(v []float64) []float64 {
	maxV := math.Inf(-1)
	for _, x := range v {
		if x > maxV {
			maxV = x
		}
	}
	out := make([]float64, len(v))
	sum := 0.0
	for i, x := range v {
		if math.IsInf(x, -1) {
			out[i] = 0
			continue
		}
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

func argmax(v []float64) int {
	best := 0
	for i := 1; i < len(v); i++ {
		if v[i] > v[best] {
			best = i
		}
	}
	return best
}

func topKIndices(v []float64, k int) []int {
	idxs := make([]int, len(v))
	for i := range idxs {
		idxs[i] = i
	}
	sort.SliceStable(idxs, func(i, j int) bool { return v[idxs[i]] > v[idxs[j]] })
	if k > len(idxs) {
		k = len(idxs)
	}
	return idxs[:k]
}

func maskTo(v []float64, keep []int, fill float64) []float64 {
	allowed := make(map[int]bool, len(keep))
	for _, i := range keep {
		allowed[i] = true
	}
	out := make([]float64, len(v))
	for i := range v {
		if !allowed[i] {
			out[i] = fill
		} else {
			out[i] = v[i]
		}
	}
	return out
}

func sampleFrom(probs []float64, rng *Rng) int {
	total := 0.0
	for _, p := range probs {
		total += p
	}
	if total <= 0 {
		return argmax(probs)
	}
	r := rng.Float64() * total
	acc := 0.0
	for i, p := range probs {
		acc += p
		if r <= acc {
			return i
		}
	}
	return argmax(probs)
}

// nucleus implementation of top-p sampling.
func nucleus(probs []float64, p float64, rng *Rng) (int, error) {
	if p <= 0 || p > 1 {
		return 0, fmt.Errorf("top_p must be in (0,1], got %f", p)
	}
	type ip struct {
		i int
		p float64
	}
	pairs := make([]ip, len(probs))
	for i, x := range probs {
		pairs[i] = ip{i, x}
	}
	sort.SliceStable(pairs, func(a, b int) bool { return pairs[a].p > pairs[b].p })

	// Keep the smallest set whose mass reaches p.
	var kept []ip
	cum := 0.0
	for _, x := range pairs {
		kept = append(kept, x)
		cum += x.p
		if cum >= p {
			break
		}
	}
	if len(kept) == 0 {
		return argmax(probs), nil
	}

	// Renormalize and sample.
	renorm := make([]float64, len(probs))
	sum := 0.0
	for _, x := range kept {
		sum += x.p
	}
	for _, x := range kept {
		renorm[x.i] = x.p / sum
	}
	return sampleFrom(renorm, rng), nil
}

// Beam is a hypothesis in beam search.
type Beam struct {
	Tokens []int
	Score  float64
	Done   bool
}

// BeamSearchConfig holds beam search parameters.
type BeamSearchConfig struct {
	BeamWidth     int
	MaxLength     int
	LengthPenalty float64
	EarlyStop     bool
}

// DefaultBeamConfig returns defaults.
func DefaultBeamConfig() BeamSearchConfig {
	return BeamSearchConfig{BeamWidth: 4, MaxLength: 64, LengthPenalty: 1.0, EarlyStop: true}
}

// BeamSearch performs beam search given a step function that returns
// log-probabilities for the next token given the current prefix.
func BeamSearch(step func(prefix []int) []float64, cfg BeamSearchConfig, eosID, bosID int) []Beam {
	if cfg.BeamWidth <= 0 {
		cfg.BeamWidth = 1
	}
	if cfg.MaxLength <= 0 {
		cfg.MaxLength = 64
	}
	if cfg.LengthPenalty <= 0 {
		cfg.LengthPenalty = 1.0
	}

	beams := []Beam{{Tokens: []int{bosID}, Score: 0}}
	for stepIdx := 0; stepIdx < cfg.MaxLength; stepIdx++ {
		var candidates []Beam
		allDone := true
		for _, b := range beams {
			if b.Done {
				candidates = append(candidates, b)
				continue
			}
			allDone = false
			logprobs := step(b.Tokens)
			if len(logprobs) == 0 {
				// Degenerate step: keep the beam unchanged.
				candidates = append(candidates, b)
				continue
			}
			idxs := topKIndices(logprobs, cfg.BeamWidth)
			for _, id := range idxs {
				nb := Beam{
					Tokens: append(append([]int(nil), b.Tokens...), id),
					Score:  b.Score + logprobs[id],
				}
				if id == eosID {
					nb.Done = true
				}
				candidates = append(candidates, nb)
			}
		}
		// Keep the best beams.
		sort.SliceStable(candidates, func(i, j int) bool {
			return normalized(candidates[i], cfg.LengthPenalty) > normalized(candidates[j], cfg.LengthPenalty)
		})
		if len(candidates) > cfg.BeamWidth {
			candidates = candidates[:cfg.BeamWidth]
		}
		beams = candidates
		if allDone && cfg.EarlyStop {
			break
		}
	}
	return beams
}

// normalized applies length normalization to a beam score.
func normalized(b Beam, penalty float64) float64 {
	n := float64(len(b.Tokens))
	if n <= 0 {
		return 0
	}
	return b.Score / math.Pow(n, penalty)
}

// StreamConfig configures token streaming.
type StreamConfig struct {
	BufferSize  int
	EchoPrompt  bool
	StopStrings []string
	StopTokens  []int
}

// DefaultStreamConfig returns defaults.
func DefaultStreamConfig() StreamConfig {
	return StreamConfig{BufferSize: 1}
}

// TokenStream converts generated tokens into text chunks.
type TokenStream struct {
	config   StreamConfig
	detok    func(id int) string
	mu       sync.Mutex
	pending  string
	emitted  int
	stopped  bool
	OnChunk  func(chunk string)
	OnFinish func(full string)
}

// NewTokenStream creates a token stream.
func NewTokenStream(cfg StreamConfig, detok func(id int) string) *TokenStream {
	return &TokenStream{config: cfg, detok: detok}
}

// Push feeds a token into the stream.
func (ts *TokenStream) Push(id int) string {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	if ts.stopped {
		return ""
	}
	for _, s := range ts.config.StopTokens {
		if s == id {
			ts.stopped = true
			return ""
		}
	}
	text := ""
	if ts.detok != nil {
		text = ts.detok(id)
	}
	ts.pending += text
	ts.emitted++

	var emit string
	if ts.config.BufferSize <= 1 {
		emit = ts.pending
		ts.pending = ""
	} else if len(ts.pending) >= ts.config.BufferSize {
		emit = ts.pending
		ts.pending = ""
	}
	if ts.OnChunk != nil && emit != "" {
		ts.OnChunk(emit)
	}
	return emit
}

// Flush emits any buffered text and finishes the stream.
func (ts *TokenStream) Flush() string {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	full := ts.pending
	ts.pending = ""
	if ts.OnFinish != nil {
		ts.OnFinish(full)
	}
	return full
}

// Stop stops the stream.
func (ts *TokenStream) Stop() { ts.stopped = true }

// Stopped reports whether the stream has stopped.
func (ts *TokenStream) Stopped() bool { return ts.stopped }

// Emitted returns the number of tokens pushed.
func (ts *TokenStream) Emitted() int { return ts.emitted }

// GenerationConfig bundles decode settings.
type GenerationConfig struct {
	MaxNewTokens int
	Strategy     Strategy
	Temperature  float64
	TopK         int
	TopP         float64
	BeamWidth    int
	UseBeam      bool
	StopStrings  []string
	StopTokens   []int
	Stream       bool
}

// DefaultGenerationConfig returns sensible defaults.
func DefaultGenerationConfig() GenerationConfig {
	return GenerationConfig{
		MaxNewTokens: 128,
		Strategy:     Greedy,
		Temperature:  1.0,
		TopK:         0,
		TopP:         1.0,
		BeamWidth:    1,
	}
}

// SamplerFromConfig builds a sampler from a generation config.
func SamplerFromConfig(cfg GenerationConfig, seed uint64) *Sampler {
	return &Sampler{
		Strategy: cfg.Strategy,
		Temp:     cfg.Temperature,
		TopK:     cfg.TopK,
		TopP:     cfg.TopP,
		Rand:     NewRng(seed),
	}
}
