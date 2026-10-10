package inference

import "testing"

func TestSpeculativeDecoderAllAccepted(t *testing.T) {
	// Draft proposes tokens 10..13. The target's own argmax agrees with
	// the draft for the first n positions and adds a bonus token, so
	// every draft token is accepted plus one bonus token.
	base := 10
	mk := func(n int) []TokenProb {
		out := make([]TokenProb, n)
		for i := 0; i < n; i++ {
			out[i] = TokenProb{Token: base + i, Prob: 1.0}
		}
		return out
	}
	sd, _ := NewSpeculativeDecoder(DefaultSpeculativeConfig(),
		func(ctx interface{}, prefix []int, n int) []TokenProb { return mk(n) },
		func(ctx interface{}, prefix []int, n int) []TokenProb { return mk(n) },
	)
	out, err := sd.DecodeStep(nil, []int{0})
	if err != nil {
		t.Fatal(err)
	}
	if len(out) == 0 {
		t.Fatal("expected tokens")
	}
	if sd.AcceptanceRate() < 0.99 {
		t.Errorf("expected high acceptance, got %f", sd.AcceptanceRate())
	}
	if sd.Speedup() < 1 {
		t.Errorf("expected speedup > 1, got %f", sd.Speedup())
	}
}

func TestSpeculativeDecoderRejects(t *testing.T) {
	sd, _ := NewSpeculativeDecoder(nil,
		func(ctx interface{}, prefix []int, n int) []TokenProb {
			out := make([]TokenProb, n)
			for i := 0; i < n; i++ {
				out[i] = TokenProb{Token: 99, Prob: 1} // always wrong
			}
			return out
		},
		func(ctx interface{}, prefix []int, n int) []TokenProb {
			out := make([]TokenProb, n)
			for i := 0; i < n; i++ {
				out[i] = TokenProb{Token: 7, Prob: 1}
			}
			return out
		},
	)
	out, err := sd.DecodeStep(nil, []int{0})
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 {
		t.Fatalf("expected only the correction token, got %d", len(out))
	}
	if out[0] != 7 {
		t.Errorf("expected correction token 7, got %d", out[0])
	}
	if sd.AcceptanceRate() != 0 {
		t.Errorf("expected 0 acceptance, got %f", sd.AcceptanceRate())
	}
}

func TestSpeculativeDecoderNilRejected(t *testing.T) {
	if _, err := NewSpeculativeDecoder(nil, nil, nil); err == nil {
		t.Error("expected error for nil functions")
	}
}

func TestSpeculativeDecoderType(t *testing.T) {
	// The decoder is a pointer type; verify nil-safe construction path.
	sd, err := NewSpeculativeDecoder(nil,
		func(ctx interface{}, p []int, n int) []TokenProb { return []TokenProb{{Token: 1}} },
		func(ctx interface{}, p []int, n int) []TokenProb { return []TokenProb{{Token: 1}, {Token: 2}} },
	)
	if err != nil || sd == nil {
		t.Fatal("expected decoder")
	}
	if sd.AcceptanceRate() != 0 {
		t.Error("fresh decoder should have 0 acceptance rate")
	}
}

func TestKVCache(t *testing.T) {
	c := NewKVCache(2, 4)
	if _, _, ok := c.Get(0); ok {
		t.Error("expected empty cache miss")
	}
	c.Put(0, []float64{1, 2}, []float64{3, 4})
	k, v, ok := c.Get(0)
	if !ok {
		t.Fatal("expected hit")
	}
	if len(k) != 2 || len(v) != 2 {
		t.Errorf("got %d %d", len(k), len(v))
	}
	hits, misses, _ := c.Stats()
	if hits == 0 || misses == 0 {
		t.Errorf("expected mixed hit/miss, got hits=%d misses=%d", hits, misses)
	}
	_ = c.HitRate()
}

func TestKVCacheEviction(t *testing.T) {
	c := NewKVCache(1, 2)
	c.Put(0, []float64{1, 2, 3, 4, 5}, []float64{1})
	out, _, _ := c.Get(0)
	if len(out) != 2 {
		t.Errorf("expected eviction to 2, got %d", len(out))
	}
	if out[0] != 4 || out[1] != 5 {
		t.Error("expected newest entries retained")
	}
}

func TestKVCacheClear(t *testing.T) {
	c := NewKVCache(2, 4)
	c.Put(0, []float64{1}, []float64{1})
	c.Clear()
	if _, _, ok := c.Get(0); ok {
		t.Error("expected cleared cache")
	}
}

func TestSlidingWindowKVCache(t *testing.T) {
	c := NewSlidingWindowKVCache(2, 8, 4)
	if c.Window() != 4 {
		t.Errorf("expected window 4, got %d", c.Window())
	}
}

func TestPagedKVCacheAllocFree(t *testing.T) {
	c := NewPagedKVCache(4, 8)
	blocks, err := c.AllocateBlocks(1, 2)
	if err != nil {
		t.Fatal(err)
	}
	if len(blocks) != 2 {
		t.Errorf("expected 2 blocks, got %d", len(blocks))
	}
	if c.FreeBlockCount() != 6 {
		t.Errorf("expected 6 free, got %d", c.FreeBlockCount())
	}
	if c.Utilization() != 0.25 {
		t.Errorf("expected utilization 0.25, got %f", c.Utilization())
	}
	c.FreeBlocks(1)
	if c.FreeBlockCount() != 8 {
		t.Errorf("expected 8 free, got %d", c.FreeBlockCount())
	}
}

func TestPagedKVCacheOOM(t *testing.T) {
	c := NewPagedKVCache(4, 2)
	if _, err := c.AllocateBlocks(1, 5); err == nil {
		t.Error("expected out of blocks error")
	}
}

func TestVerificationResultStruct(t *testing.T) {
	vr := VerificationResult{Accepted: 2, Correction: 3, AcceptedTokens: []int{1, 2}}
	if vr.Accepted != 2 || vr.Correction != 3 {
		t.Error("struct fields")
	}
}

func TestDefaultSpecConfig(t *testing.T) {
	c := DefaultSpeculativeConfig()
	if c.DraftLen != 4 {
		t.Errorf("expected DraftLen 4, got %d", c.DraftLen)
	}
	if c.Temperature != 1.0 {
		t.Errorf("expected temp 1.0, got %f", c.Temperature)
	}
}
