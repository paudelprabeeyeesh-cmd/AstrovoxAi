package main

import (
	"context"

	"github.com/astrovox/astrovox/internal/tools"
)

// scriptedProposer returns a fixed sequence then stops. It is the same
// double the agent package uses in its tests, reused here so the reference
// server runs the real loop code rather than a shortcut around it.
type scriptedProposer struct {
	calls []*tools.Call
	err   error
}

func (s *scriptedProposer) Propose(_ context.Context, _ int, _ []tools.Result) (*tools.Call, error) {
	if s.err != nil {
		return nil, s.err
	}
	if len(s.calls) == 0 {
		return nil, nil
	}
	next := s.calls[0]
	s.calls = s.calls[1:]
	return next, nil
}
