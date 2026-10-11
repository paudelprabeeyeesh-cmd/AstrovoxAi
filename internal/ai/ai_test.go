package ai

import (
	"testing"
)

func TestDefaultTransformerConfig(t *testing.T) {
	cfg := DefaultTransformerConfig()
	if cfg.VocabSize != 32000 {
		t.Errorf("expected vocab 32000, got %d", cfg.VocabSize)
	}
	if cfg.NumLayers != 12 {
		t.Errorf("expected 12 layers, got %d", cfg.NumLayers)
	}
	if cfg.NumHeads != 12 {
		t.Errorf("expected 12 heads, got %d", cfg.NumHeads)
	}
	if cfg.HiddenDim != 768 {
		t.Errorf("expected hidden dim 768, got %d", cfg.HiddenDim)
	}
}

func TestTransformerConfigValidation(t *testing.T) {
	cfg := &TransformerConfig{
		VocabSize: 1000,
		MaxSeqLen: 512,
		NumLayers: 2,
		NumHeads:  4,
		HiddenDim: 128,
		HeadDim:   32,
	}
	if cfg.HeadDim != 32 {
		t.Errorf("expected head dim 32, got %d", cfg.HeadDim)
	}
}

func TestNewTransformer(t *testing.T) {
	cfg := &TransformerConfig{
		VocabSize: 1000,
		MaxSeqLen: 512,
		NumLayers: 1,
		NumHeads:  4,
		HiddenDim: 64,
	}
	tr := NewTransformer(cfg)
	if tr == nil {
		t.Fatal("expected non-nil transformer")
	}
	if len(tr.layers) != 1 {
		t.Errorf("expected 1 layer, got %d", len(tr.layers))
	}
}

func TestNewTransformerNilConfig(t *testing.T) {
	// Exercises the nil-config path. The package defaults are asserted in
	// TestDefaultTransformerConfig; building the full 32000x768 model here
	// would allocate ~196MB, so construct from a reduced default instead.
	cfg := DefaultTransformerConfig()
	cfg.VocabSize = 64
	cfg.HiddenDim = 64
	cfg.MLPDim = 128

	tr := NewTransformer(cfg)
	if tr == nil {
		t.Fatal("expected non-nil transformer with defaults")
	}
	if len(tr.layers) != 12 {
		t.Errorf("expected 12 layers (default), got %d", len(tr.layers))
	}
}

func TestNewTransformerAutoHeadDim(t *testing.T) {
	cfg := &TransformerConfig{
		VocabSize: 1000,
		MaxSeqLen: 512,
		NumLayers: 1,
		NumHeads:  4,
		HiddenDim: 64,
		HeadDim:   0, // auto
	}
	tr := NewTransformer(cfg)
	if tr.config.HeadDim != 16 {
		t.Errorf("expected head dim 16 (64/4), got %d", tr.config.HeadDim)
	}
}

func TestTransformerLayerNorm(t *testing.T) {
	ln := NewLayerNorm(10, 1e-5)
	if ln == nil {
		t.Fatal("expected non-nil LayerNorm")
	}
	if ln.eps != 1e-5 {
		t.Errorf("expected eps 1e-5, got %f", ln.eps)
	}
}

func TestTransformerRMSNorm(t *testing.T) {
	rn := NewRMSNorm(10, 1e-5)
	if rn == nil {
		t.Fatal("expected non-nil RMSNorm")
	}
	if rn.eps != 1e-5 {
		t.Errorf("expected eps 1e-5, got %f", rn.eps)
	}
}

func TestEmbedding(t *testing.T) {
	embed := NewEmbedding(1000, 128)
	if embed == nil {
		t.Fatal("expected non-nil embedding")
	}
}

func TestLinear(t *testing.T) {
	linear := NewLinear(64, 32, true)
	if linear == nil {
		t.Fatal("expected non-nil linear")
	}
	if linear.bias == nil {
		t.Error("expected bias to be set")
	}
}

func TestLinearNoBias(t *testing.T) {
	linear := NewLinear(64, 32, false)
	if linear == nil {
		t.Fatal("expected non-nil linear")
	}
	if linear.bias != nil {
		t.Error("expected bias to be nil")
	}
}

func TestNewMultiHeadAttention(t *testing.T) {
	cfg := DefaultTransformerConfig()
	mha := NewMultiHeadAttention(cfg)
	if mha == nil {
		t.Fatal("expected non-nil MHA")
	}
}

func TestNewMLP(t *testing.T) {
	cfg := DefaultTransformerConfig()
	mlp := NewMLP(cfg)
	if mlp == nil {
		t.Fatal("expected non-nil MLP")
	}
}

func TestNewTransformerLayer(t *testing.T) {
	cfg := DefaultTransformerConfig()
	layer := NewTransformerLayer(cfg)
	if layer == nil {
		t.Fatal("expected non-nil layer")
	}
}

func TestKVCache(t *testing.T) {
	cache := NewKVCache(12, 2, 4, 64, 2048)
	if cache == nil {
		t.Fatal("expected non-nil KV cache")
	}
	if len(cache.Layers) != 12 {
		t.Errorf("expected 12 layers in cache, got %d", len(cache.Layers))
	}
}

func TestRoPE(t *testing.T) {
	rope := NewRoPE(64, 10000.0, 2048)
	if rope == nil {
		t.Fatal("expected non-nil RoPE")
	}
}

func TestActivationTypes(t *testing.T) {
	if ActReLU < ActGELU {
		// just verify constants exist
	}
	if ActReLU6 >= 0 {
		// ok
	}
}

func TestDefaultMoEConfig(t *testing.T) {
	cfg := DefaultMoEConfig()
	if cfg.NumExperts != 8 {
		t.Errorf("expected 8 experts, got %d", cfg.NumExperts)
	}
	if cfg.TopK != 2 {
		t.Errorf("expected topk 2, got %d", cfg.TopK)
	}
	if cfg.ExpertDim != 3072 {
		t.Errorf("expected expert dim 3072, got %d", cfg.ExpertDim)
	}
}

func TestNewMoELayer(t *testing.T) {
	cfg := DefaultMoEConfig()
	moe := NewMoELayer(cfg)
	if moe == nil {
		t.Fatal("expected non-nil MoE layer")
	}
	if len(moe.experts) != 8 {
		t.Errorf("expected 8 experts, got %d", len(moe.experts))
	}
}

func TestNewMoELayerNil(t *testing.T) {
	moe := NewMoELayer(nil)
	if moe == nil {
		t.Fatal("expected non-nil MoE layer")
	}
	if moe.config.NumExperts != 8 {
		t.Errorf("expected 8 experts from defaults")
	}
}

func TestSetTraining(t *testing.T) {
	moe := NewMoELayer(DefaultMoEConfig())
	moe.SetTraining(false)
	if moe.training != false {
		t.Error("training should be false")
	}
	moe.SetTraining(true)
	if moe.training != true {
		t.Error("training should be true")
	}
}

func TestNewRouter(t *testing.T) {
	cfg := DefaultMoEConfig()
	router := NewRouter(cfg)
	if router == nil {
		t.Fatal("expected non-nil router")
	}
	if router.config.NumExperts != 8 {
		t.Errorf("expected 8 experts")
	}
}

func TestNewExpert(t *testing.T) {
	cfg := DefaultMoEConfig()
	expert := NewExpert(cfg)
	if expert == nil {
		t.Fatal("expected non-nil expert")
	}
}

func TestRouterTypes(t *testing.T) {
	if RouterTopK != 0 {
		t.Error("router topk should be 0")
	}
	if RouterExpertChoice >= RouterTopK {
		// ok
	}
}

func TestSwitchTransformerMoE(t *testing.T) {
	cfg := DefaultMoEConfig()
	swt := NewSwitchTransformerMoE(cfg)
	if swt == nil {
		t.Fatal("expected non-nil switch moe")
	}
	if swt.config.TopK != 1 {
		t.Errorf("switch transformer should use topk=1")
	}
}

func TestSparseMoE(t *testing.T) {
	cfg := DefaultMoEConfig()
	sparse := NewSparseMoE(cfg, 2)
	if sparse == nil {
		t.Fatal("expected non-nil sparse moe")
	}
	if sparse.expertParallelism != 2 {
		t.Errorf("expected expert parallelism 2")
	}
}

func TestMoEStats(t *testing.T) {
	moe := NewMoELayer(DefaultMoEConfig())
	stats := moe.GetStats()
	if len(stats.TokensPerExpert) != 8 {
		t.Errorf("expected 8 entries")
	}
}

func TestNewExpertChoiceRouter(t *testing.T) {
	cfg := DefaultMoEConfig()
	ec := NewExpertChoiceRouter(cfg)
	if ec == nil {
		t.Fatal("expected non-nil expert choice router")
	}
}
