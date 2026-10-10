// Package diffusion implements diffusion models: noise schedules,
// forward noising, and DDPM/DDIM sampling steps.
package diffusion

import (
	"errors"
	"fmt"
	"math"
)

// ScheduleType identifies a noise schedule.
type ScheduleType int

const (
	ScheduleLinear ScheduleType = iota
	ScheduleCosine
	ScheduleQuadratic
)

func (s ScheduleType) String() string {
	switch s {
	case ScheduleCosine:
		return "cosine"
	case ScheduleQuadratic:
		return "quadratic"
	default:
		return "linear"
	}
}

// Schedule holds precomputed diffusion coefficients.
type Schedule struct {
	Timesteps int
	Betas     []float64
	Alphas    []float64
	AlphaBars []float64
	Type      ScheduleType
}

// NewSchedule builds a schedule for the given type and timestep count.
func NewSchedule(scheduleType ScheduleType, timesteps int) (*Schedule, error) {
	if timesteps <= 0 {
		return nil, errors.New("timesteps must be positive")
	}
	s := &Schedule{Timesteps: timesteps, Type: scheduleType}
	s.Betas = make([]float64, timesteps)
	s.Alphas = make([]float64, timesteps)
	s.AlphaBars = make([]float64, timesteps)

	betaStart, betaEnd := 1e-4, 0.02
	for t := 0; t < timesteps; t++ {
		var beta float64
		switch scheduleType {
		case ScheduleCosine:
			// Nichol & Dhariwal cosine schedule.
			frac := float64(t) / float64(timesteps)
			ab := math.Cos((frac+0.008)/1.008*math.Pi/2) / math.Cos((0.0+0.008)/1.008*math.Pi/2)
			ab = math.Max(ab, 1e-5)
			if t > 0 {
				s.AlphaBars[t] = s.AlphaBars[t-1] * ab
			} else {
				s.AlphaBars[t] = ab
			}
			continue
		case ScheduleQuadratic:
			beta = betaStart + (betaEnd-betaStart)*(float64(t)/float64(timesteps))*(float64(t)/float64(timesteps))
		default:
			beta = betaStart + (betaEnd-betaStart)*(float64(t)/float64(timesteps-1))
		}
		if beta < 0 {
			beta = 0
		}
		s.Betas[t] = beta
		s.Alphas[t] = 1.0 - beta
		if t == 0 {
			s.AlphaBars[t] = s.Alphas[t]
		} else {
			s.AlphaBars[t] = s.AlphaBars[t-1] * s.Alphas[t]
		}
	}
	return s, nil
}

// Beta returns beta at timestep t.
func (s *Schedule) Beta(t int) (float64, error) {
	if t < 0 || t >= s.Timesteps {
		return 0, fmt.Errorf("%w: %d", ErrTimestepOutOfRange, t)
	}
	return s.Betas[t], nil
}

// AlphaBar returns the cumulative product of alphas at timestep t.
func (s *Schedule) AlphaBar(t int) (float64, error) {
	if t < 0 || t >= s.Timesteps {
		return 0, fmt.Errorf("%w: %d", ErrTimestepOutOfRange, t)
	}
	return s.AlphaBars[t], nil
}

// SignalToNoise returns the log-SNR at timestep t.
func (s *Schedule) SignalToNoise(t int) (float64, error) {
	ab, err := s.AlphaBar(t)
	if err != nil {
		return 0, err
	}
	if 1-ab <= 0 {
		return 0, nil
	}
	return math.Log(ab) - math.Log(1-ab), nil
}

// Diffusion errors.
var ErrTimestepOutOfRange = errors.New("timestep out of range")

// QSample performs the forward noising step: x_t = sqrt(ab)*x0 + sqrt(1-ab)*noise.
func (s *Schedule) QSample(x0, noise []float64, t int) ([]float64, error) {
	ab, err := s.AlphaBar(t)
	if err != nil {
		return nil, err
	}
	if len(x0) != len(noise) {
		return nil, errors.New("x0 and noise must have the same length")
	}
	sqrtAb := math.Sqrt(ab)
	sqrtOneMinus := math.Sqrt(1 - ab)
	out := make([]float64, len(x0))
	for i := range x0 {
		out[i] = sqrtAb*x0[i] + sqrtOneMinus*noise[i]
	}
	return out, nil
}

// PredictX0 reverses the forward process: x0 = (xt - sqrt(1-ab)*eps) / sqrt(ab).
func (s *Schedule) PredictX0(xt, eps []float64, t int) ([]float64, error) {
	ab, err := s.AlphaBar(t)
	if err != nil {
		return nil, err
	}
	if len(xt) != len(eps) {
		return nil, errors.New("xt and eps must have the same length")
	}
	sqrtAb := math.Sqrt(ab)
	sqrtOneMinus := math.Sqrt(1 - ab)
	out := make([]float64, len(xt))
	for i := range xt {
		out[i] = (xt[i] - sqrtOneMinus*eps[i]) / sqrtAb
	}
	return out, nil
}

// PosteriorMean returns the DDPM posterior mean q(x_{t-1} | x_t, x0).
func (s *Schedule) PosteriorMean(x0, xt []float64, t int) ([]float64, error) {
	if t <= 0 {
		return append([]float64(nil), x0...), nil
	}
	if t >= s.Timesteps {
		return nil, fmt.Errorf("%w: %d", ErrTimestepOutOfRange, t)
	}
	alpha := s.Alphas[t]
	abPrev := s.AlphaBars[t-1]
	ab := s.AlphaBars[t]
	if 1-ab <= 0 || 1-abPrev <= 0 {
		return nil, errors.New("invalid alpha bars for posterior")
	}
	c1 := math.Sqrt(abPrev) * (1 - alpha) / (1 - ab)
	c2 := math.Sqrt(alpha) * (1 - abPrev) / (1 - ab)
	out := make([]float64, len(xt))
	for i := range xt {
		out[i] = c1*x0[i] + c2*xt[i]
	}
	return out, nil
}

// PosteriorVariance returns the DDPM posterior variance beta_tilde.
func (s *Schedule) PosteriorVariance(t int) (float64, error) {
	if t <= 0 {
		return 0, nil
	}
	if t >= s.Timesteps {
		return 0, fmt.Errorf("%w: %d", ErrTimestepOutOfRange, t)
	}
	abPrev := s.AlphaBars[t-1]
	beta := s.Betas[t]
	return beta * (1 - abPrev) / (1 - s.AlphaBars[t]), nil
}

// DDPMStep performs one ancestral DDPM denoising step.
func (s *Schedule) DDPMStep(xt, eps []float64, t int) ([]float64, error) {
	x0, err := s.PredictX0(xt, eps, t)
	if err != nil {
		return nil, err
	}
	mean, err := s.PosteriorMean(x0, xt, t)
	if err != nil {
		return nil, err
	}
	if t == 0 {
		return mean, nil
	}
	variance, err := s.PosteriorVariance(t)
	if err != nil {
		return nil, err
	}
	// Deterministic pseudo-noise keeps results reproducible in tests.
	noise := make([]float64, len(xt))
	for i := range noise {
		noise[i] = pseudoNoise(i, t)
	}
	scale := math.Sqrt(variance)
	out := make([]float64, len(xt))
	for i := range xt {
		out[i] = mean[i] + scale*noise[i]
	}
	return out, nil
}

// DDIMStep performs one deterministic DDIM step:
//
//	x_{tPrev} = sqrt(ab_{tPrev}) * x0 + sqrt(1 - ab_{tPrev}) * eps
//
// where x0 is predicted from x_t. With eta > 0 the stochastic variant
// adds sigma * noise to the direction term.
func (s *Schedule) DDIMStep(xt, eps []float64, t, tPrev int, eta float64) ([]float64, error) {
	if tPrev < 0 || tPrev >= t {
		return nil, errors.New("tPrev must be in [0, t)")
	}
	x0, err := s.PredictX0(xt, eps, t)
	if err != nil {
		return nil, err
	}
	abPrev := s.AlphaBars[tPrev]
	sqrtOneMinusPrev := math.Sqrt(1 - abPrev)
	direction := make([]float64, len(xt))
	for i := range xt {
		direction[i] = sqrtOneMinusPrev * eps[i]
	}
	if eta > 0 {
		sigma := eta * math.Sqrt((1-abPrev)/(1-s.AlphaBars[t]))
		for i := range xt {
			direction[i] += sigma * pseudoNoise(i, t)
		}
	}
	sqrtAbPrev := math.Sqrt(abPrev)
	out := make([]float64, len(xt))
	for i := range xt {
		out[i] = sqrtAbPrev*x0[i] + direction[i]
	}
	return out, nil
}

// pseudoNoise is a deterministic pseudo-random value in [-1, 1) derived
// from an index and timestep, used where real Gaussian noise is not needed.
func pseudoNoise(i, t int) float64 {
	x := float64((i+1)*2654435761 + t*40503)
	x = math.Mod(x, 4294967296.0)
	return x/4294967296.0*2 - 1
}

// Sampler drives the reverse process using a noise predictor.
type Sampler struct {
	Schedule *Schedule
	// PredictNoise returns eps_hat(x_t, t) for a batch of values.
	PredictNoise func(xt []float64, t int) ([]float64, error)
}

// NewDDIMSampler creates a DDIM sampler with a fixed number of steps.
func NewDDIMSampler(s *Schedule, steps int, predict func([]float64, int) ([]float64, error)) (*Sampler, error) {
	if s == nil || predict == nil {
		return nil, errors.New("schedule and predictor are required")
	}
	if steps <= 0 {
		return nil, errors.New("steps must be positive")
	}
	return &Sampler{Schedule: s, PredictNoise: predict}, nil
}

// DDIMSample runs the full deterministic DDIM chain from pure noise.
func (sm *Sampler) DDIMSample(xT []float64, steps int) ([]float64, error) {
	if steps <= 0 || steps > sm.Schedule.Timesteps {
		return nil, errors.New("steps out of range")
	}
	// Build a descending timestep ladder with uniform stride.
	ladder := sm.scheduleLadder(steps)
	x := append([]float64(nil), xT...)
	for i := 0; i < len(ladder)-1; i++ {
		t := ladder[i]
		tPrev := ladder[i+1]
		eps, err := sm.PredictNoise(x, t)
		if err != nil {
			return nil, err
		}
		x, err = sm.Schedule.DDIMStep(x, eps, t, tPrev, 0)
		if err != nil {
			return nil, err
		}
	}
	return x, nil
}

// DDPMSample runs the full ancestral DDPM chain.
func (sm *Sampler) DDPMSample(xT []float64) ([]float64, error) {
	x := append([]float64(nil), xT...)
	for t := sm.Schedule.Timesteps - 1; t >= 0; t-- {
		eps, err := sm.PredictNoise(x, t)
		if err != nil {
			return nil, err
		}
		x, err = sm.Schedule.DDPMStep(x, eps, t)
		if err != nil {
			return nil, err
		}
	}
	return x, nil
}

// scheduleLadder builds a descending timestep ladder for `steps` inferences.
func (sm *Sampler) scheduleLadder(steps int) []int {
	var ladder []int
	stride := sm.Schedule.Timesteps / steps
	for t := sm.Schedule.Timesteps - 1; t >= 0; t -= stride {
		ladder = append(ladder, t)
	}
	if len(ladder) == 0 || ladder[len(ladder)-1] != 0 {
		ladder = append(ladder, 0)
	}
	return ladder
}

// TrainingLossScore computes a simplified epsilon-prediction objective:
// ||eps - eps_hat(x_t, t)||^2 / n.
func LossScore(eps, epsHat []float64) (float64, error) {
	if len(eps) != len(epsHat) {
		return 0, errors.New("length mismatch")
	}
	if len(eps) == 0 {
		return 0, errors.New("empty input")
	}
	sum := 0.0
	for i := range eps {
		d := eps[i] - epsHat[i]
		sum += d * d
	}
	return sum / float64(len(eps)), nil
}