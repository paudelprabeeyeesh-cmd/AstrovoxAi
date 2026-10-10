package rl

import (
	"testing"
)

func TestReplayBufferPushLen(t *testing.T) {
	b, err := NewReplayBuffer(3, false)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 5; i++ {
		b.Push(Experience{Action: i})
	}
	if b.Len() != 3 {
		t.Errorf("expected capacity bound 3, got %d", b.Len())
	}
}

func TestNewReplayBufferInvalid(t *testing.T) {
	if _, err := NewReplayBuffer(0, false); err == nil {
		t.Error("expected capacity error")
	}
	if _, err := NewReplayBuffer(-1, false); err == nil {
		t.Error("expected capacity error")
	}
}

func TestReplayBufferSampleUniform(t *testing.T) {
	b, _ := NewReplayBuffer(10, false)
	for i := 0; i < 10; i++ {
		b.Push(Experience{Action: i})
	}
	rng := NewRng(7)
	batch, err := b.Sample(5, rng)
	if err != nil {
		t.Fatal(err)
	}
	if len(batch) != 5 {
		t.Errorf("expected 5, got %d", len(batch))
	}
}

func TestReplayBufferSampleEmpty(t *testing.T) {
	b, _ := NewReplayBuffer(4, false)
	if _, err := b.Sample(2, NewRng(1)); err != ErrEmptyBuffer {
		t.Errorf("expected empty buffer error, got %v", err)
	}
}

func TestReplayBufferSampleInvalid(t *testing.T) {
	b, _ := NewReplayBuffer(4, false)
	b.Push(Experience{})
	if _, err := b.Sample(0, NewRng(1)); err == nil {
		t.Error("expected sample size error")
	}
}

func TestReplayBufferPrioritized(t *testing.T) {
	b, _ := NewReplayBuffer(4, true)
	b.Push(Experience{Action: 0, Priority: 0.0}) // fallback weight
	b.Push(Experience{Action: 1, Priority: 1e6})
	seen := map[int]int{}
	rng := NewRng(3)
	for i := 0; i < 200; i++ {
		batch, err := b.Sample(1, rng)
		if err != nil {
			t.Fatal(err)
		}
		seen[batch[0].Action]++
	}
	if seen[1] < seen[0] {
		t.Errorf("high-priority item should be sampled more: %v", seen)
	}
}

func TestReplayBufferClear(t *testing.T) {
	b, _ := NewReplayBuffer(4, false)
	b.Push(Experience{})
	b.Clear()
	if b.Len() != 0 {
		t.Error("expected empty")
	}
}

func TestRngRange(t *testing.T) {
	r := NewRng(42)
	for i := 0; i < 100; i++ {
		f := r.Float64()
		if f < 0 || f >= 1 {
			t.Fatalf("float out of range: %f", f)
		}
		n := r.Intn(7)
		if n < 0 || n >= 7 {
			t.Fatalf("int out of range: %d", n)
		}
	}
	if r.Intn(0) != 0 {
		t.Error("Intn(0)")
	}
}

func TestRngDeterministic(t *testing.T) {
	a, b := NewRng(99), NewRng(99)
	for i := 0; i < 5; i++ {
		if a.Float64() != b.Float64() {
			t.Fatal("same seed must match")
		}
	}
}

func TestEpsilonGreedy(t *testing.T) {
	// epsilon=0 always exploits.
	id, err := EpsilonGreedy([]float64{1, 3, 2}, 0, NewRng(1))
	if err != nil {
		t.Fatal(err)
	}
	if id != 1 {
		t.Errorf("expected argmax, got %d", id)
	}
	// epsilon=1 always explores.
	seen := map[int]bool{}
	for i := 0; i < 100; i++ {
		id, _ := EpsilonGreedy([]float64{1, 3, 2}, 1, NewRng(uint64(i+1)))
		seen[id] = true
	}
	if len(seen) < 2 {
		t.Error("expected exploration to hit multiple actions")
	}
}

func TestEpsilonGreedyInvalid(t *testing.T) {
	if _, err := EpsilonGreedy(nil, 0, NewRng(1)); err != ErrInvalidShape {
		t.Errorf("expected invalid shape, got %v", err)
	}
	if _, err := EpsilonGreedy([]float64{1}, 2, NewRng(1)); err == nil {
		t.Error("expected epsilon range error")
	}
}

func TestDiscount(t *testing.T) {
	got := Discount([]float64{1, 1, 1}, 1.0, nil)
	for i, v := range got {
		want := float64(3 - i)
		if v != want {
			t.Errorf("element %d: got %f, want %f", i, v, want)
		}
	}
	// done=true truncates the tail.
	got = Discount([]float64{1, 1, 1}, 1.0, []bool{false, true, false})
	if got[1] != 1 || got[2] != 1 {
		t.Errorf("expected truncation, got %v", got)
	}
}

func TestNormalizeReturns(t *testing.T) {
	out := NormalizeReturns([]float64{1, 2, 3}, 1e-8)
	mean := 0.0
	for _, v := range out {
		mean += v
	}
	if mean > 1e-6 || mean < -1e-6 {
		t.Errorf("expected zero mean, got %f", mean)
	}
	if NormalizeReturns(nil, 1) != nil {
		t.Error("expected nil for empty")
	}
}

func TestTDError(t *testing.T) {
	e := Experience{Reward: 1, Done: true}
	if d := TDError(e, []float64{5}, 0.99, 2); d != -1 {
		t.Errorf("expected -1, got %f", d)
	}
	// Not done: target = r + gamma * max(qNext).
	e2 := Experience{Reward: 1, Done: false}
	if d := TDError(e2, []float64{2, 4}, 0.5, 0); d != 3 {
		t.Errorf("expected 3, got %f", d)
	}
}

func TestLinearQNet(t *testing.T) {
	n, err := NewLinearQNet(2, 3)
	if err != nil {
		t.Fatal(err)
	}
	n.B[1] = 0.5
	q, err := n.Forward([]float64{1, 0})
	if err != nil {
		t.Fatal(err)
	}
	if q[1] != 0.5 {
		t.Errorf("expected bias passthrough, got %v", q)
	}
	if err := n.SGDStep([]float64{1, 1}, []float64{1, 0, 0}, 0.1); err != nil {
		t.Fatal(err)
	}
	// Weight for action 0 must have decreased (gradient descent).
	if n.W[0][0] >= 0 || n.W[1][0] >= 0 {
		t.Error("expected weight update")
	}
}

func TestLinearQNetInvalid(t *testing.T) {
	if _, err := NewLinearQNet(0, 3); err != ErrInvalidShape {
		t.Error("expected state dim error")
	}
	n, _ := NewLinearQNet(2, 2)
	if _, err := n.Forward([]float64{1}); err != ErrInvalidShape {
		t.Error("expected shape error")
	}
	if err := n.SGDStep([]float64{1}, []float64{1, 1}, 0.1); err != ErrInvalidShape {
		t.Error("expected shape error")
	}
}

func TestPolicyGradientAgent(t *testing.T) {
	a, err := NewPolicyGradientAgent(2, 3)
	if err != nil {
		t.Fatal(err)
	}
	probs, err := a.Probs([]float64{0.5, -0.5})
	if err != nil {
		t.Fatal(err)
	}
	sum := 0.0
	for _, p := range probs {
		sum += p
	}
	if sum < 0.999 || sum > 1.001 {
		t.Errorf("expected softmax sum 1, got %f", sum)
	}
	rng := NewRng(5)
	counts := map[int]int{}
	for i := 0; i < 100; i++ {
		act, err := a.Select([]float64{0.5, -0.5}, rng)
		if err != nil {
			t.Fatal(err)
		}
		if act < 0 || act >= 3 {
			t.Fatalf("action out of range: %d", act)
		}
		counts[act]++
	}
	if len(counts) < 2 {
		t.Error("expected multiple actions sampled")
	}
	if err := a.Update([]float64{0.5, -0.5}, 1, 1.0, 0.1); err != nil {
		t.Fatal(err)
	}
}

func TestPolicyGradientInvalid(t *testing.T) {
	if _, err := NewPolicyGradientAgent(0, 3); err != ErrInvalidShape {
		t.Error("expected dims error")
	}
	a, _ := NewPolicyGradientAgent(2, 3)
	if _, err := a.Probs([]float64{1}); err != ErrInvalidShape {
		t.Error("expected shape error")
	}
	if err := a.Update([]float64{1, 2}, 99, 1, 0.1); err != ErrInvalidShape {
		t.Error("expected action range error")
	}
}