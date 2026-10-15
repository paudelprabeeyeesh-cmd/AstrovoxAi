package model

import "github.com/astrovox/astrovox/internal/errors"

// Schedule and trainer configuration errors. They use the engine-wide
// typed codes so callers classify them without string matching.
func errNilSchedule() error {
	return errors.New(errors.CodeInvalidArgument, "nil schedule")
}

func errBadSchedule(what string, value float64) error {
	return errors.New(errors.CodeInvalidArgument, "invalid schedule: "+what).
		WithField("value", value)
}

func errUnknownSchedule(name string) error {
	return errors.New(errors.CodeInvalidArgument, "unknown schedule kind").
		WithField("name", name)
}

func errNilTrainerConfig() error {
	return errors.New(errors.CodeInvalidArgument, "nil trainer config")
}

func errTrainerConfig(what string) error {
	return errors.New(errors.CodeInvalidArgument, "invalid trainer config: "+what)
}

func errNoData() error {
	return errors.New(errors.CodeInvalidArgument, "trainer requires a dataset")
}

// errNilTrainerConfigUnused is intentionally not referenced: nil configs
// are impossible with a value receiver.
var _ = errNilTrainerConfig
