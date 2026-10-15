package model

import "math"

// Schedule maps a step index (0-based) to a learning rate. Schedules are
// pure functions: no state, no clock, so a resumed run reproduces the
// uninterrupted trajectory exactly.
type Schedule interface {
	// LR returns the learning rate for the given 0-based step.
	LR(step int) float64
	// Name identifies the schedule in checkpoints and logs.
	Name() string
}

// ConstantSchedule returns the base rate at every step.
type ConstantSchedule struct {
	Base float64
}

// Name implements Schedule.
func (ConstantSchedule) Name() string { return "constant" }

// LR implements Schedule.
func (s ConstantSchedule) LR(int) float64 { return s.Base }

// StepSchedule multiplies the base rate by Gamma every StepSize steps:
// lr(step) = Base * Gamma^(step / StepSize).
type StepSchedule struct {
	Base     float64
	StepSize int
	Gamma    float64
}

// Name implements Schedule.
func (StepSchedule) Name() string { return "step" }

// LR implements Schedule.
func (s StepSchedule) LR(step int) float64 {
	if s.StepSize <= 0 {
		return s.Base
	}
	return s.Base * math.Pow(s.Gamma, float64(step/s.StepSize))
}

// CosineSchedule anneals from Base to Min over Total steps following a
// cosine curve, then holds Min.
type CosineSchedule struct {
	Base  float64
	Min   float64
	Total int
}

// Name implements Schedule.
func (CosineSchedule) Name() string { return "cosine" }

// LR implements Schedule.
func (s CosineSchedule) LR(step int) float64 {
	if s.Total <= 0 || step >= s.Total {
		return s.Min
	}
	if step < 0 {
		step = 0
	}
	cos := math.Cos(math.Pi * float64(step) / float64(s.Total))
	return s.Min + (s.Base-s.Min)*(1+cos)/2
}

// Config validates a schedule configuration and reports the first
// problem it finds, so a bad schedule is a startup error rather than a
// silent flat line.
func validateSchedule(s Schedule) error {
	if s == nil {
		return errNilSchedule()
	}
	switch v := s.(type) {
	case ConstantSchedule:
		if v.Base <= 0 {
			return errBadSchedule("constant base must be positive", v.Base)
		}
	case StepSchedule:
		if v.Base <= 0 {
			return errBadSchedule("step base must be positive", v.Base)
		}
		if v.StepSize <= 0 {
			return errBadSchedule("step size must be positive", float64(v.StepSize))
		}
		if v.Gamma <= 0 || v.Gamma > 1 {
			return errBadSchedule("step gamma must be in (0, 1]", v.Gamma)
		}
	case CosineSchedule:
		if v.Base <= 0 {
			return errBadSchedule("cosine base must be positive", v.Base)
		}
		if v.Min < 0 || v.Min > v.Base {
			return errBadSchedule("cosine min must be in [0, base]", v.Min)
		}
		if v.Total <= 0 {
			return errBadSchedule("cosine total must be positive", float64(v.Total))
		}
	default:
		return errUnknownSchedule(s.Name())
	}
	return nil
}
