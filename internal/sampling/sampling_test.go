package sampling

import (
	"math"
	"testing"
)

func TestRngDeterministic(t *testing.T) {
	a := NewRng(12345)
	b := NewRng(12345)
	for i := 0; i < 10; i++ {
		if a.Float64() != b.Float64() {
			t.Fatal("same seed must produce same sequence")
		}
	}
	c := NewRng(999)
	if a.Float64() == c.Float64() {
		t.Error("different seeds should differ")
	}
}

func TestRngRange(t *testing.T) {
	r := NewRng(7)
	for i := 0; i < 100; i++ {
		v := r.Float64()
		if v < 0 || v >= 1 {
			t.Fatalf("value out of range: %f", v)
		}
	}
}

func TestGreedySampler(t *testing.T) {
	s := DefaultSampler()
	id, err := s.Sample([]float64{1, 5, 2}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if id != 1 {
		t.Errorf("expected argmax index 1, got %d", id)
	}
}

func TestGreedySamplerEmpty(t *testing.T) {
	s := DefaultSampler()
	if _, err := s.Sample(nil, nil); err == nil {
		t.Error("expected error for empty logits")
	}
}

func TestTemperatureSampler(t *testing.T) {
	s := &Sampler{Strategy: Temperature, Temp: 1.0, Rand: NewRng(1)}
	// A peaked distribution should almost always return the max.
	counts := map[int]int{}
	for i := 0; i < 200; i++ {
		id, err := s.Sample([]float64{0, 10, 0}, nil)
		if err != nil {
			t.Fatal(err)
		}
		counts[id]++
	}
	if counts[1] < 180 {
		t.Errorf("expected mostly index 1, got %v", counts)
	}
}

func TestZeroTempIsGreedy(t *testing.T) {
	s := &Sampler{Strategy: Temperature, Temp: 0, Rand: NewRng(1)}
	id, _ := s.Sample([]float64{1, 2, 3}, nil)
	if id != 2 {
		t.Errorf("expected greedy index 2, got %d", id)
	}
}

func TestTopKSampler(t *testing.T) {
	s := &Sampler{Strategy: TopK, TopK: 1, Temp: 1, Rand: NewRng(1)}
	id, err := s.Sample([]float64{1, 3, 2}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if id != 1 {
		t.Errorf("top-1 should pick the max, got %d", id)
	}
}

func TestTopKSamplerMulti(t *testing.T) {
	s := &Sampler{Strategy: TopK, TopK: 2, Temp: 1, Rand: NewRng(3)}
	for i := 0; i < 50; i++ {
		id, err := s.Sample([]float64{10, 5, 0}, nil)
		if err != nil {
			t.Fatal(err)
		}
		if id != 0 && id != 1 {
			t.Fatalf("expected only top-2 tokens, got %d", id)
		}
	}
}

func TestTopPSampler(t *testing.T) {
	s := &Sampler{Strategy: TopP, TopP: 0.5, Temp: 1, Rand: NewRng(5)}
	// With p=0.5 only the dominant token survives nucleus filtering.
	id, err := s.Sample([]float64{1, 6, 1}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if id != 1 {
		t.Errorf("expected the dominant token, got %d", id)
	}
}

func TestTopPInvalidRange(t *testing.T) {
	s := &Sampler{Strategy: TopP, TopP: 2.0, Temp: 1, Rand: NewRng(5)}
	if _, err := s.Sample([]float64{0.5, 0.5}, nil); err == nil {
		t.Error("expected error for top_p > 1")
	}
}

func TestRepetitionPenalty(t *testing.T) {
	base := []float64{5, 1, 1}
	s := &Sampler{Strategy: Greedy, RepetitionPenalty: 2.0}
	id, err := s.Sample(base, []int{0})
	if err != nil {
		t.Fatal(err)
	}
	if id != 0 {
		t.Errorf("expected index 0, got %d", id)
	}
	if base[0] != 5 {
		t.Error("penalty must not mutate the caller's slice")
	}
}

func TestSoftmaxSumsToOne(t *testing.T) {
	p := softmax([]float64{1, 2, 3})
	sum := 0.0
	for _, v := range p {
		sum += v
	}
	if math.Abs(sum-1.0) > 1e-9 {
		t.Errorf("sum = %f", sum)
	}
	if p[2] <= p[0] {
		t.Error("softmax must preserve ordering")
	}
}

func TestTopKIndices(t *testing.T) {
	idxs := topKIndices([]float64{1, 5, 3, 4}, 2)
	if len(idxs) != 2 || idxs[0] != 1 || idxs[1] != 3 {
		t.Errorf("got %v", idxs)
	}
}

func TestArgmax(t *testing.T) {
	if argmax([]float64{1, 9, 3}) != 1 {
		t.Error("argmax")
	}
}

func TestStrategyString(t *testing.T) {
	if Greedy.String() != "greedy" || TopP.String() != "top_p" {
		t.Error("strategy strings")
	}
	if Strategy(99).String() != "unknown" {
		t.Error("unknown strategy string")
	}
}

func TestBeamSearch(t *testing.T) {
	// Always proposes token (last+1).
	step := func(prefix []int) []float64 {
		out := make([]float64, 8)
		for i := range out {
			out[i] = -10
		}
		next := 0
		if len(prefix) > 0 {
			next = prefix[len(prefix)-1] + 1
		}
		if next < len(out) {
			out[next] = 0
		}
		return out
	}
	beams := BeamSearch(step, DefaultBeamConfig(), 7, 0)
	if len(beams) == 0 {
		t.Fatal("expected beams")
	}
	best := beams[0]
	if len(best.Tokens) == 0 || best.Tokens[0] != 0 {
		t.Error("beam should start from bos")
	}
}

func TestBeamSearchEmptyLogits(t *testing.T) {
	beams := BeamSearch(func(p []int) []float64 { return nil }, DefaultBeamConfig(), 1, 0)
	if len(beams) != 1 {
		t.Errorf("expected 1 fallback beam, got %d", len(beams))
	}
}

func TestBeamSearchStopsAtEos(t *testing.T) {
	step := func(p []int) []float64 {
		out := make([]float64, 4)
		for i := range out {
			out[i] = 0
		}
		return out
	}
	cfg := DefaultBeamConfig()
	cfg.MaxLength = 10
	beams := BeamSearch(step, cfg, 3, 0)
	found := false
	for _, b := range beams {
		for _, tok := range b.Tokens[1:] {
			if tok == 3 {
				found = true
			}
		}
	}
	if !found {
		t.Error("expected a beam to reach eos")
	}
}

func TestTokenStream(t *testing.T) {
	ts := NewTokenStream(DefaultStreamConfig(), func(id int) string { return string(rune('a' + id)) })
	if got := ts.Push(0); got != "a" {
		t.Errorf("got %q", got)
	}
	if ts.Emitted() != 1 {
		t.Error("emitted count")
	}
	if got := ts.Flush(); got != "" {
		t.Errorf("expected empty flush, got %q", got)
	}
}

func TestTokenStreamBuffering(t *testing.T) {
	cfg := DefaultStreamConfig()
	cfg.BufferSize = 3
	ts := NewTokenStream(cfg, func(id int) string { return "x" })
	if got := ts.Push(0); got != "" {
		t.Errorf("expected buffering, got %q", got)
	}
	if got := ts.Push(0); got != "" {
		t.Errorf("expected buffering, got %q", got)
	}
	if got := ts.Push(0); got != "xxx" {
		t.Errorf("expected flush at buffer size, got %q", got)
	}
}

func TestTokenStreamStopToken(t *testing.T) {
	cfg := DefaultStreamConfig()
	cfg.StopTokens = []int{9}
	ts := NewTokenStream(cfg, func(id int) string { return "y" })
	ts.Push(9)
	if !ts.Stopped() {
		t.Error("stream should be stopped")
	}
	if got := ts.Push(0); got != "" {
		t.Errorf("expected no output after stop, got %q", got)
	}
}

func TestTokenStreamCallbacks(t *testing.T) {
	var chunks []string
	ts := NewTokenStream(DefaultStreamConfig(), func(id int) string { return "z" })
	ts.OnChunk = func(c string) { chunks = append(chunks, c) }
	ts.Push(0)
	ts.Push(0)
	if len(chunks) != 2 {
		t.Errorf("expected 2 chunks, got %d", len(chunks))
	}
}

func TestSamplerFromConfig(t *testing.T) {
	cfg := DefaultGenerationConfig()
	s := SamplerFromConfig(cfg, 42)
	if s.Rand == nil {
		t.Error("expected rng")
	}
}

func TestDefaultGenerationConfig(t *testing.T) {
	c := DefaultGenerationConfig()
	if c.MaxNewTokens != 128 || c.Strategy != Greedy {
		t.Error("defaults")
	}
}