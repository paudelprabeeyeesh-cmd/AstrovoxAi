package tools

import (
	"fmt"
	"sort"
	"strings"
)

// Generated docs for the registry.
//
// A model chooses between tools from text it is shown, so the catalogue is
// generated from the registrations rather than written twice. A hand-written
// catalogue drifts the moment a tool is added, and the drift is invisible: the
// model asks for a tool with the wrong arguments and the failure looks like a
// model error rather than a documentation one.

// Catalogue renders every registered tool as a model-readable block.
//
// Deterministic, because it goes into a prompt: two builds of the same registry
// must produce the same text or an eval's prompt changes between runs for no
// reason the operator caused.
func (r *Registry) Catalogue() string {
	names := r.Names()

	var b strings.Builder
	b.WriteString("# Available tools\n")
	for _, name := range names {
		schema, ok := r.Schema(name)
		if !ok {
			continue
		}
		b.WriteString("\n")
		b.WriteString(schema.Describe())
	}
	return b.String()
}

// Describe renders one tool as a model-readable block.
func (s Schema) Describe() string {
	var b strings.Builder
	fmt.Fprintf(&b, "## %s\n", s.Name)
	if s.Description != "" {
		fmt.Fprintf(&b, "%s\n", s.Description)
	}
	fmt.Fprintf(&b, "risk: %s", s.Risk)
	if s.Risk.RequiresApproval() {
		b.WriteString(" (requires approval)")
	}
	b.WriteString("\n")

	if len(s.Params) == 0 {
		b.WriteString("arguments: none\n")
		return b.String()
	}

	b.WriteString("arguments:\n")
	for _, name := range sortedKeys(toStringMap(s.Params)) {
		p := s.Params[name]
		fmt.Fprintf(&b, "  - %s: %s", name, p.Kind)
		if p.Required {
			b.WriteString(" (required)")
		} else if p.Default != nil {
			fmt.Fprintf(&b, " (default %v)", p.Default)
		}
		if len(p.Enum) > 0 {
			fmt.Fprintf(&b, " [one of: %s]", strings.Join(p.Enum, ", "))
		}
		if p.MinLength > 0 {
			fmt.Fprintf(&b, " [min %d]", p.MinLength)
		}
		if p.MaxLength > 0 {
			fmt.Fprintf(&b, " [max %d]", p.MaxLength)
		}
		b.WriteString("\n")
	}
	return b.String()
}

// JSONSchema renders the tool as a JSON Schema object, for providers that
// accept function definitions natively.
//
// The shape is the standard one, but the risk is carried in the description:
// providers do not have a place for it, and a model that cannot see that a tool
// will spend money cannot be trusted not to call it.
func (s Schema) JSONSchema() map[string]interface{} {
	properties := map[string]interface{}{}
	required := []string{}

	for name, p := range s.Params {
		prop := map[string]interface{}{"type": jsonType(p.Kind)}
		if len(p.Enum) > 0 {
			prop["enum"] = p.Enum
		}
		if p.MinLength > 0 {
			prop["minLength"] = p.MinLength
		}
		if p.MaxLength > 0 {
			prop["maxLength"] = p.MaxLength
		}
		if p.Default != nil {
			prop["default"] = p.Default
		}
		properties[name] = prop
		if p.Required {
			required = append(required, name)
		}
	}

	sort.Strings(required)

	description := s.Description
	if s.Risk.RequiresApproval() {
		description = fmt.Sprintf(
			"%s [risk: %s — requires approval before it runs]", description, s.Risk)
	}

	return map[string]interface{}{
		"name":        s.Name,
		"description": description,
		"parameters": map[string]interface{}{
			"type":       "object",
			"properties": properties,
			"required":   required,
		},
	}
}

// CatalogueJSON renders every tool as provider function definitions.
func (r *Registry) CatalogueJSON() []map[string]interface{} {
	names := r.Names()
	out := make([]map[string]interface{}, 0, len(names))
	for _, name := range names {
		if schema, ok := r.Schema(name); ok {
			out = append(out, schema.JSONSchema())
		}
	}
	return out
}

// jsonType maps an internal kind to a JSON Schema type.
func jsonType(k Kind) string {
	switch k {
	case KindString:
		return "string"
	case KindInt:
		return "integer"
	case KindFloat:
		return "number"
	case KindBool:
		return "boolean"
	case KindList:
		return "array"
	default:
		return "string"
	}
}

// toStringMap copies a map whose values are not comparable, so it can be
// passed to the sorted-keys helper that expects map[string]interface{}.
func toStringMap(m map[string]Param) map[string]interface{} {
	out := make(map[string]interface{}, len(m))
	for k, v := range m {
		out[k] = v
	}
	return out
}
