package main

import (
	"context"

	"github.com/astrovox/astrovox/internal/chat"
)

// referenceVendor is a stand-in provider, not a model. It is a real
// chat.Provider so the orchestrator, spend gate, and handlers are all
// exercisable without credentials.
//
// It carries the two failure modes explicitly, so the handler's error paths
// can be driven from a test rather than being unreachable.
type referenceVendor struct{}

func (referenceVendor) Name() string { return "reference-vendor" }

// Complete implements chat.Provider with a fixed three-chunk response.
func (referenceVendor) Complete(ctx context.Context, req *chat.Request) (chat.Stream, error) {
	chunks := []string{"This is a ", "reference ", "response."}
	out := make(chan chat.Chunk, len(chunks)+1)
	for _, c := range chunks {
		out <- chat.Chunk{Delta: c}
	}
	// The usage is what the gate meters: a real provider reports the tokens
	// it consumed, which is what makes the cap converge on real usage.
	out <- chat.Chunk{Done: true, Usage: chat.Usage{InputTokens: 10, OutputTokens: 6}}
	close(out)
	return out, nil
}
