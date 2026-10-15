package model

import (
	"fmt"

	"github.com/astrovox/astrovox/internal/checkpoint"
	"github.com/astrovox/astrovox/internal/errors"
)

// ToCheckpoint snapshots a model's parameters (with hierarchical names
// from Flatten) into a checkpoint structure. Optimizer state, if any, is
// attached by the caller before writing.
func ToCheckpoint(modelName string, m Module) (*checkpoint.FileCheckpoint, error) {
	params, err := Flatten(m)
	if err != nil {
		return nil, err
	}
	cp := &checkpoint.FileCheckpoint{
		Version: checkpoint.FileFormatVersion,
		Model:   modelName,
	}
	for _, p := range params {
		cp.Parameters = append(cp.Parameters, checkpoint.NamedTensor{
			Name:  p.Name,
			Shape: p.Var.Value.Shape().Dims(),
			Data:  append([]float64(nil), p.Var.Value.Float64()...),
		})
	}
	return cp, nil
}

// RestoreFromCheckpoint loads parameters from cp into m.
//
// The checkpoint must name exactly the model's parameters: an extra,
// missing, or differently-shaped entry is an error, because silently
// skipping parameters would restore a half-updated model that trains
// from the wrong state.
func RestoreFromCheckpoint(m Module, cp *checkpoint.FileCheckpoint) error {
	if cp == nil {
		return errors.New(errors.CodeInvalidArgument, "nil checkpoint")
	}
	params, err := Flatten(m)
	if err != nil {
		return err
	}
	byName := make(map[string]int, len(params))
	for i, p := range params {
		byName[p.Name] = i
	}
	loaded := make([]bool, len(params))
	for _, t := range cp.Parameters {
		idx, ok := byName[t.Name]
		if !ok {
			return errors.New(errors.CodeInvalidArgument,
				"checkpoint names a parameter the model does not have").
				WithField("name", t.Name)
		}
		v := params[idx].Var.Value
		if !sameShape(v.Shape().Dims(), t.Shape) || v.NumElements() != len(t.Data) {
			return errors.New(errors.CodeShapeMismatch,
				"checkpoint parameter shape does not match the model").
				WithField("name", t.Name).
				WithField("checkpoint", fmt.Sprint(t.Shape)).
				WithField("model", v.Shape().String())
		}
		copy(v.Float64(), t.Data)
		loaded[idx] = true
	}
	for i, ok := range loaded {
		if !ok {
			return errors.New(errors.CodeInvalidArgument,
				"checkpoint is missing a model parameter").
				WithField("name", params[i].Name)
		}
	}
	return nil
}

func sameShape(a, b []int) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
