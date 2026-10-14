package chat

import "sort"

// ---------------------------------------------------------------------------
// Capability registry
// ---------------------------------------------------------------------------

// Capabilities describes what a model can do, so a router never has to guess.
//
// The registry exists because a router that does not know a model's limits
// makes two mistakes that are both expensive and neither is visible at the
// call site: it sends a prompt longer than the context window and gets an
// error after the fact, and it asks a model for tool calls it cannot make and
// gets a graceful refusal that the caller reads as a model failure.
type Capabilities struct {
	// Model is the model identifier this entry describes.
	Model string `json:"model"`
	// ContextTokens is the maximum prompt + completion length.
	ContextTokens int `json:"context_tokens"`
	// MaxOutputTokens is the maximum completion length on its own, which is
	// not the remainder of the context window: some models cap output far
	// below their context.
	MaxOutputTokens int `json:"max_output_tokens"`
	// SupportsTools reports whether the model accepts a tool schema.
	SupportsTools bool `json:"supports_tools"`
	// SupportsVision reports whether the model accepts images.
	SupportsVision bool `json:"supports_vision"`
	// Streams reports whether the provider emits token deltas.
	Streams bool `json:"streams"`
	// Tier orders models by capability, not by price. A router that needs
	// reasoning asks for a tier rather than naming a model.
	Tier int `json:"tier"`
	// Price is the per-1K-token rate, kept with the capability because a
	// routing decision that ignores cost trades money away silently.
	Price Price `json:"price"`
}

// DefaultCapabilities is the registry shipped with the package.
//
// The numbers are the published limits as of the version this was written.
// They are data, not code, precisely so they can be corrected without a change
// to the router.
var DefaultCapabilities = map[string]Capabilities{
	"gpt-4o-mini": {
		Model: "gpt-4o-mini", ContextTokens: 128000, MaxOutputTokens: 16384,
		SupportsTools: true, SupportsVision: true, Streams: true, Tier: 2,
		Price: PriceFor("gpt-4o-mini"),
	},
	"gpt-4o": {
		Model: "gpt-4o", ContextTokens: 128000, MaxOutputTokens: 16384,
		SupportsTools: true, SupportsVision: true, Streams: true, Tier: 3,
		Price: PriceFor("gpt-4o"),
	},
	"gpt-4-turbo": {
		Model: "gpt-4-turbo", ContextTokens: 128000, MaxOutputTokens: 4096,
		SupportsTools: true, Streams: true, Tier: 3,
		Price: PriceFor("gpt-4-turbo"),
	},
	"gpt-4": {
		Model: "gpt-4", ContextTokens: 8192, MaxOutputTokens: 4096,
		Streams: true, Tier: 3,
		Price: PriceFor("gpt-4"),
	},
	"gpt-3.5-turbo": {
		Model: "gpt-3.5-turbo", ContextTokens: 16385, MaxOutputTokens: 4096,
		SupportsTools: true, Streams: true, Tier: 1,
		Price: PriceFor("gpt-3.5-turbo"),
	},
	"claude-3-haiku": {
		Model: "claude-3-haiku", ContextTokens: 200000, MaxOutputTokens: 4096,
		SupportsTools: true, SupportsVision: true, Streams: true, Tier: 1,
		Price: PriceFor("claude-3-haiku"),
	},
	"claude-3-sonnet": {
		Model: "claude-3-sonnet", ContextTokens: 200000, MaxOutputTokens: 4096,
		SupportsTools: true, SupportsVision: true, Streams: true, Tier: 3,
		Price: PriceFor("claude-3-sonnet"),
	},
	"claude-3-opus": {
		Model: "claude-3-opus", ContextTokens: 200000, MaxOutputTokens: 4096,
		SupportsTools: true, SupportsVision: true, Streams: true, Tier: 4,
		Price: PriceFor("claude-3-opus"),
	},
}

// Registry is the set of known models.
type Registry struct {
	byModel map[string]Capabilities
}

// NewRegistry returns a registry containing only the given entries. An empty
// call returns an empty registry rather than a default, so a test that builds
// a registry gets exactly what it asked for.
func NewRegistry(entries ...Capabilities) *Registry {
	r := &Registry{byModel: make(map[string]Capabilities, len(entries))}
	for _, e := range entries {
		r.byModel[e.Model] = e
	}
	return r
}

// DefaultRegistry returns a registry with the shipped entries.
func DefaultRegistry() *Registry {
	out := make([]Capabilities, 0, len(DefaultCapabilities))
	for _, c := range DefaultCapabilities {
		out = append(out, c)
	}
	return NewRegistry(out...)
}

// Register adds or replaces an entry.
func (r *Registry) Register(c Capabilities) {
	r.byModel[c.Model] = c
}

// Get returns an entry, or false.
func (r *Registry) Get(model string) (Capabilities, bool) {
	c, ok := r.byModel[model]
	return c, ok
}

// Known returns every model in the registry, sorted by name so a listing is
// reproducible.
func (r *Registry) Known() []string {
	out := make([]string, 0, len(r.byModel))
	for m := range r.byModel {
		out = append(out, m)
	}
	sort.Strings(out)
	return out
}

// StrictFallback returns the capabilities assumed for an unregistered model.
//
// It is the most restrictive combination in the registry, because the two
// failure modes are asymmetric: assuming too much capability routes a request
// the model cannot serve and it fails after the round trip, while assuming too
// little merely picks a safer model. A router must never invent capability.
func (r *Registry) StrictFallback() Capabilities {
	if len(r.byModel) == 0 {
		return Capabilities{
			ContextTokens: 4096, MaxOutputTokens: 1024,
			SupportsTools: false, SupportsVision: false, Streams: true, Tier: 0,
		}
	}
	strict := Capabilities{
		ContextTokens: 1 << 30, MaxOutputTokens: 1 << 30,
		SupportsTools: true, SupportsVision: true, Streams: true, Tier: 100,
	}
	for _, c := range r.byModel {
		if c.ContextTokens < strict.ContextTokens {
			strict.ContextTokens = c.ContextTokens
		}
		if c.MaxOutputTokens < strict.MaxOutputTokens {
			strict.MaxOutputTokens = c.MaxOutputTokens
		}
		if !c.SupportsTools {
			strict.SupportsTools = false
		}
		if !c.SupportsVision {
			strict.SupportsVision = false
		}
		if !c.Streams {
			strict.Streams = false
		}
		if c.Tier < strict.Tier {
			strict.Tier = c.Tier
		}
	}
	return strict
}

// Fits reports whether a prompt of the given token count can be served. The
// comparison uses the context window with room for the requested output,
// because a prompt that fits exactly but leaves no room for a reply still
// fails.
func (c Capabilities) Fits(promptTokens, maxOutputTokens int) bool {
	if maxOutputTokens <= 0 {
		maxOutputTokens = 1024
	}
	if maxOutputTokens > c.MaxOutputTokens {
		return false
	}
	return promptTokens+maxOutputTokens <= c.ContextTokens
}

// Supports reports whether the model can serve this request's demands. A
// request with images sent to a text-only model is refused here rather than
// degraded into a silently wrong answer.
func (c Capabilities) Supports(wantsTools, wantsVision bool) bool {
	if wantsTools && !c.SupportsTools {
		return false
	}
	if wantsVision && !c.SupportsVision {
		return false
	}
	return true
}
