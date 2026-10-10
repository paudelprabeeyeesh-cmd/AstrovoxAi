package diffusion

import (
	"math"
	"testing"
)

func TestNewScheduleLinear(t *testing.T) {
	s, err := NewSchedule(ScheduleLinear, 10)
	if err != nil {
		t.Fatal(err)
	}
	if s.Timesteps != 10 || len(s.Betas) != 10 {
		t.Fatal("schedule shape")
	}
	// Betas must increase monotonically and stay within (0,1).
	for i := 1; i < len(s.Betas); i++ {
		if s.Betas[i] < s.Betas[i-1] {
			t.Error("betas must be non-decreasing")
		}
	}
	for i, b := range s.Betas {
		if b <= 0 || b >= 1 {
			t.Errorf("beta %d out of range: %f", i, b)
		}
	}
	// Alpha bars must be strictly decreasing.
	for i := 1; i < len(s.AlphaBars); i++ {
		if s.AlphaBars[i] >= s.AlphaBars[i-1] {
			t.Error("alpha bars must decrease")
		}
	}
}

func TestNewScheduleInvalid(t *testing.T) {
	if _, err := NewSchedule(ScheduleLinear, 0); err == nil {
		t.Error("expected timesteps error")
	}
	if _, err := NewSchedule(ScheduleLinear, -5); err == nil {
		t.Error("expected timesteps error")
	}
}

func TestScheduleTypes(t *testing.T) {
	sq, _ := NewSchedule(ScheduleQuadratic, 20)
	sc, _ := NewSchedule(ScheduleCosine, 20)
	if sq.Type != ScheduleQuadratic || sc.Type != ScheduleCosine {
		t.Error("schedule type")
	}
	if ScheduleLinear.String() != "linear" || ScheduleCosine.String() != "cosine" {
		t.Error("schedule type strings")
	}
	// Cosine alpha bars must remain in (0,1].
	for i, ab := range sc.AlphaBars {
		if ab <= 0 || ab > 1 {
			t.Errorf("cosine alpha bar %d out of range: %f", i, ab)
		}
	}
}

func TestScheduleAccessors(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 8)
	if _, err := s.Beta(-1); err == nil {
		t.Error("expected range error")
	}
	if _, err := s.Beta(8); err == nil {
		t.Error("expected range error")
	}
	if _, err := s.AlphaBar(100); err == nil {
		t.Error("expected range error")
	}
	snr, err := s.SignalToNoise(4)
	if err != nil {
		t.Fatal(err)
	}
	if math.Abs(snr) > 20 {
		t.Errorf("unexpected SNR %f", snr)
	}
}

func TestQSampleAndPredictRoundTrip(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 50)
	x0 := []float64{0.5, -1.0, 2.0}
	noise := []float64{0.1, 0.2, -0.3}
	xt, err := s.QSample(x0, noise, 25)
	if err != nil {
		t.Fatal(err)
	}
	// x0 recovered from xt and noise must match the original.
	recovered, err := s.PredictX0(xt, noise, 25)
	if err != nil {
		t.Fatal(err)
	}
	for i := range x0 {
		if math.Abs(recovered[i]-x0[i]) > 1e-9 {
			t.Errorf("element %d: got %f, want %f", i, recovered[i], x0[i])
		}
	}
}

func TestQSampleLengthMismatch(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 10)
	if _, err := s.QSample([]float64{1}, []float64{1, 2}, 1); err == nil {
		t.Error("expected length error")
	}
}

func TestPosteriorAtEndpoint(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 10)
	if v, err := s.PosteriorVariance(0); err != nil || v != 0 {
		t.Errorf("t=0 must have zero variance, got %f (%v)", v, err)
	}
	mean, err := s.PosteriorMean([]float64{1, 2}, []float64{3, 4}, 0)
	if err != nil {
		t.Fatal(err)
	}
	if mean[0] != 1 {
		t.Error("t=0 mean should be x0")
	}
	v, err := s.PosteriorVariance(5)
	if err != nil {
		t.Fatal(err)
	}
	if v <= 0 || v >= 1 {
		t.Errorf("variance out of range: %f", v)
	}
	if _, err := s.PosteriorVariance(999); err == nil {
		t.Error("expected range error")
	}
}

func TestDDPMStepDeterministic(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 20)
	xt := []float64{0.2, -0.4}
	eps := []float64{0.1, 0.1}
	a, err := s.DDPMStep(xt, eps, 10)
	if err != nil {
		t.Fatal(err)
	}
	b, _ := s.DDPMStep(xt, eps, 10)
	for i := range a {
		if a[i] != b[i] {
			t.Fatal("DDPM step must be deterministic")
		}
	}
	// t=0 must return the posterior mean exactly.
	final, err := s.DDPMStep(xt, eps, 0)
	if err != nil {
		t.Fatal(err)
	}
	if len(final) != 2 {
		t.Error("dimension")
	}
}

func TestDDIMStep(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 20)
	xt := []float64{0.5}
	eps := []float64{0.1}
	out, err := s.DDIMStep(xt, eps, 10, 5, 0)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 {
		t.Fatal("dimension")
	}
	if _, err := s.DDIMStep(xt, eps, 5, 5, 0); err == nil {
		t.Error("expected tPrev < t error")
	}
	if _, err := s.DDIMStep(xt, eps, 10, -1, 0); err == nil {
		t.Error("expected tPrev >= 0 error")
	}
	// Stochastic variant must still produce output.
	if _, err := s.DDIMStep(xt, eps, 10, 5, 0.5); err != nil {
		t.Fatal(err)
	}
}

func TestSamplerDDIMFull(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 20)
	// A perfect predictor that returns the correct noise lets the chain
	// recover x0 from pure noise.
	target := []float64{0.5, -0.25}
	noise := []float64{0.1, -0.2}
	sm, err := NewDDIMSampler(s, 4, func(xt []float64, t int) ([]float64, error) {
		// Return the "true" noise implied by the chain state.
		ab, _ := s.AlphaBar(t)
		out := make([]float64, len(xt))
		for i := range xt {
			out[i] = (xt[i] - math.Sqrt(ab)*target[i]) / math.Sqrt(1-ab)
		}
		return out, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	xT, _ := s.QSample(target, noise, 19)
	out, err := sm.DDIMSample(xT, 4)
	if err != nil {
		t.Fatal(err)
	}
	for i := range target {
		if math.Abs(out[i]-target[i]) > 0.05 {
			t.Errorf("element %d: got %f, want ~%f", i, out[i], target[i])
		}
	}
}

func TestSamplerDDPMFull(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 8)
	sm, err := NewDDIMSampler(s, 2, func(xt []float64, t int) ([]float64, error) {
		return []float64{0, 0}, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	out, err := sm.DDPMSample([]float64{0.1, 0.2})
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 2 {
		t.Fatal("dimension")
	}
}

func TestSamplerValidation(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 10)
	if _, err := NewDDIMSampler(nil, 4, func([]float64, int) ([]float64, error) { return nil, nil }); err == nil {
		t.Error("expected schedule error")
	}
	if _, err := NewDDIMSampler(s, 4, nil); err == nil {
		t.Error("expected predictor error")
	}
	if _, err := NewDDIMSampler(s, 0, func([]float64, int) ([]float64, error) { return nil, nil }); err == nil {
		t.Error("expected steps error")
	}
	sm, _ := NewDDIMSampler(s, 2, func([]float64, int) ([]float64, error) { return nil, nil })
	if _, err := sm.DDIMSample([]float64{1}, 0); err == nil {
		t.Error("expected steps range error")
	}
	if _, err := sm.DDIMSample([]float64{1}, 999); err == nil {
		t.Error("expected steps range error")
	}
}

func TestScheduleLadder(t *testing.T) {
	s, _ := NewSchedule(ScheduleLinear, 20)
	sm, _ := NewDDIMSampler(s, 4, func([]float64, int) ([]float64, error) { return nil, nil })
	ladder := sm.scheduleLadder(4)
	if len(ladder) != 5 || ladder[0] != 19 || ladder[len(ladder)-1] != 0 {
		t.Errorf("ladder: %v", ladder)
	}
}

func TestLossScore(t *testing.T) {
	if _, err := LossScore([]float64{1}, []float64{1, 2}); err == nil {
		t.Error("expected length error")
	}
	if _, err := LossScore(nil, nil); err == nil {
		t.Error("expected empty error")
	}
	v, err := LossScore([]float64{0, 0}, []float64{1, 1})
	if err != nil {
		t.Fatal(err)
	}
	if v != 1 {
		t.Errorf("expected MSE 1, got %f", v)
	}
}

func TestPseudoNoiseRange(t *testing.T) {
	for i := 0; i < 200; i++ {
		v := pseudoNoise(i, i%20)
		if v < -1 || v >= 1 {
			t.Fatalf("noise out of range: %f", v)
		}
	}
}