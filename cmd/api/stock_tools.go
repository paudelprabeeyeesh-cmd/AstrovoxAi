package main

import (
	"time"

	"github.com/astrovox/astrovox/internal/tools"
)

// stockRegistry returns the registry with the two demonstrably safe tools
// this reference server ships.
//
// Both are reads or reversible writes. An external or irreversible tool is
// deliberately absent, because without an approval UI it would be an
// unattended side effect.
func stockRegistry() *tools.Registry {
	r := tools.New()
	_ = r.Register(tools.Schema{
		Name:        "math.add",
		Description: "Add two integers.",
		Risk:        tools.RiskRead,
		Timeout:     time.Second,
		Params: map[string]tools.Param{
			"a": {Kind: tools.KindInt, Required: true},
			"b": {Kind: tools.KindInt, Required: true},
		},
	}, addTool{})

	_ = r.Register(tools.Schema{
		Name:        "note.append",
		Description: "Append a line to the caller's scratch notes.",
		Risk:        tools.RiskWrite,
		Timeout:     time.Second,
		Params: map[string]tools.Param{
			"text": {Kind: tools.KindString, Required: true, MinLength: 1, MaxLength: 512},
		},
	}, noteTool{})
	return r
}

// stockExecutor returns an executor with the default budget.
func stockExecutor() *tools.Executor {
	return tools.NewExecutor(stockRegistry(), tools.DefaultBudget())
}

// shortID derives a compact unique id from a seed. It is not a security
// token: it identifies a row, it does not authenticate one.
func shortID(seed string) string {
	h := uint64(14695981039346656037)
	for i := 0; i < len(seed); i++ {
		h ^= uint64(seed[i])
		h *= 1099511628211
	}
	const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
	b := make([]byte, 10)
	for i := range b {
		b[i] = alphabet[h%uint64(len(alphabet))]
		h /= uint64(len(alphabet))
	}
	return string(b)
}

// addTool is the arithmetic tool.
type addTool struct{}

func (addTool) Execute(args map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{
		"sum": asInt(args["a"]) + asInt(args["b"]),
	}, nil
}

// noteTool is the scratch-note tool. It returns what it would have written,
// which is the documented contract for a reference implementation.
type noteTool struct{}

func (noteTool) Execute(args map[string]interface{}) (map[string]interface{}, error) {
	return map[string]interface{}{"written": args["text"]}, nil
}

// asInt reads an integer from a JSON-decoded value, which may be float64.
func asInt(v interface{}) int {
	switch n := v.(type) {
	case int:
		return n
	case float64:
		return int(n)
	}
	return 0
}

	// web.fetch is a guard composition rather than a plain HTTP client: the
	// SSRF guard runs before the transport, so an agent cannot be pointed
	// at an internal address by a URL in its prompt.
	_ = r.Register(tools.Schema{
		Name:        "web.fetch",
		Description: "Fetch a public web page and return its text.",
		Risk:        tools.RiskRead,
		Timeout:     15 * time.Second,
		Params: map[string]tools.Param{
			"url": {Kind: tools.KindString, Required: true, MinLength: 8, MaxLength: 2048},
		},
	}, webfetch.NewTool(webfetch.NewSafeFetcher()))
