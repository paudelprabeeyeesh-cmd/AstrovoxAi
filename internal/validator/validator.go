// Package validator provides a composable rule engine for validating
// configuration, shapes, dtypes, and graph attributes with full error
// aggregation (all failures reported, not just the first).
package validator

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"github.com/astrovox/astrovox/internal/errors"
)

// Rule identifies a built-in validation rule.
type Rule int

// Built-in rules.
const (
	RuleNone Rule = iota
	RuleString
	RuleInt
	RuleFloat
	RuleBool
	RuleEmail
	RuleURL
	RuleNonEmpty
)

func (r Rule) String() string {
	switch r {
	case RuleString:
		return "string"
	case RuleInt:
		return "int"
	case RuleFloat:
		return "float"
	case RuleBool:
		return "bool"
	case RuleEmail:
		return "email"
	case RuleURL:
		return "url"
	case RuleNonEmpty:
		return "non_empty"
	default:
		return "none"
	}
}

// Constraint is a user-defined validation predicate.
type Constraint struct {
	Name  string
	Check func(value any) error
}

// Spec describes validation for one field.
type Spec struct {
	Name        string
	Required    bool
	Type        Rule
	Min, Max    float64
	HasRange    bool
	Enum        []string
	HasEnum     bool
	Pattern     *regexp.Regexp
	Constraints []Constraint
}

// Option mutates a Spec during construction.
type Option func(*Spec)

// Required marks the field as mandatory.
func Required() Option { return func(s *Spec) { s.Required = true } }

// TypeOf sets the built-in type rule.
func TypeOf(r Rule) Option { return func(s *Spec) { s.Type = r } }

// Range restricts numeric values to [min, max].
func Range(min, max float64) Option {
	return func(s *Spec) {
		s.Min, s.Max, s.HasRange = min, max, true
	}
}

// Enum restricts values to a fixed set.
func Enum(values ...string) Option {
	return func(s *Spec) { s.Enum, s.HasEnum = values, true }
}

// Pattern restricts strings to a regular expression.
func Pattern(expr string) Option {
	return func(s *Spec) {
		s.Pattern = regexp.MustCompile(expr)
	}
}

// Custom appends a user-defined constraint.
func Custom(c Constraint) Option {
	return func(s *Spec) { s.Constraints = append(s.Constraints, c) }
}

// Field builds a validation spec.
func Field(name string, opts ...Option) *Spec {
	spec := &Spec{Name: name}
	for _, opt := range opts {
		opt(spec)
	}
	return spec
}

// Validate checks a value against a spec and returns all violations.
func Validate(name string, value any, spec *Spec) []error {
	var errs []error
	if value == nil {
		if spec.Required {
			errs = append(errs, fieldError(name, "required field missing"))
		}
		return errs
	}
	if spec.Type != RuleNone {
		if err := Check(fmt.Sprint(value), spec.Type, name); err != nil {
			errs = append(errs, err)
		}
	}
	switch v := value.(type) {
	case string:
		if spec.Type == RuleNonEmpty && v == "" {
			errs = append(errs, fieldError(name, "value must not be empty"))
		}
		if spec.HasEnum {
			ok := false
			for _, e := range spec.Enum {
				if e == v {
					ok = true
					break
				}
			}
			if !ok {
				errs = append(errs, fieldError(name, fmt.Sprintf("value %q not in enum %v", v, spec.Enum)))
			}
		}
		if spec.Pattern != nil && !spec.Pattern.MatchString(v) {
			errs = append(errs, fieldError(name, fmt.Sprintf("value %q does not match pattern", v)))
		}
	case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64, float32, float64:
		if spec.HasRange {
			f := toFloat(value)
			if f < spec.Min || f > spec.Max {
				errs = append(errs, fieldError(name, fmt.Sprintf("value %v outside range [%v, %v]", f, spec.Min, spec.Max)))
			}
		}
	}
	for _, c := range spec.Constraints {
		if err := c.Check(value); err != nil {
			errs = append(errs, fieldError(name, err.Error()))
		}
	}
	return errs
}

// Check validates a string representation against a built-in rule.
func Check(raw string, rule Rule, field string) error {
	switch rule {
	case RuleInt:
		if !isInt(raw) {
			return fieldError(field, "expected integer")
		}
	case RuleFloat:
		if !isFloat(raw) {
			return fieldError(field, "expected float")
		}
	case RuleBool:
		if raw != "true" && raw != "false" {
			return fieldError(field, "expected bool")
		}
	case RuleEmail:
		if !strings.Contains(raw, "@") || !strings.Contains(raw, ".") {
			return fieldError(field, "expected email")
		}
	case RuleURL:
		if !strings.HasPrefix(raw, "http://") && !strings.HasPrefix(raw, "https://") {
			return fieldError(field, "expected http(s) URL")
		}
	}
	return nil
}

func isInt(s string) bool {
	if s == "" {
		return false
	}
	i := 0
	if s[0] == '+' || s[0] == '-' {
		i = 1
	}
	if i == len(s) {
		return false
	}
	for ; i < len(s); i++ {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
	}
	return true
}

func isFloat(s string) bool {
	if isInt(s) {
		return true
	}
	dot := false
	i := 0
	if s != "" && (s[0] == '+' || s[0] == '-') {
		i = 1
	}
	for ; i < len(s); i++ {
		switch {
		case s[i] == '.':
			if dot {
				return false
			}
			dot = true
		case s[i] < '0' || s[i] > '9':
			return false
		}
	}
	return dot
}

func toFloat(v any) float64 {
	switch n := v.(type) {
	case int:
		return float64(n)
	case int8:
		return float64(n)
	case int16:
		return float64(n)
	case int32:
		return float64(n)
	case int64:
		return float64(n)
	case uint:
		return float64(n)
	case uint8:
		return float64(n)
	case uint16:
		return float64(n)
	case uint32:
		return float64(n)
	case uint64:
		return float64(n)
	case float32:
		return float64(n)
	case float64:
		return n
	default:
		return 0
	}
}

func fieldError(field, msg string) error {
	return errors.New(errors.CodeInvalidArgument, msg).WithField("field", field)
}

// ValidateAll validates a map of values against a map of specs and aggregates
// every violation into one error.
func ValidateAll(values map[string]any, specs map[string]*Spec) error {
	var msgs []string
	for name, spec := range specs {
		errs := Validate(name, values[name], spec)
		for _, err := range errs {
			msgs = append(msgs, err.Error())
		}
	}
	if len(msgs) == 0 {
		return nil
	}
	return errors.New(errors.CodeInvalidArgument, "validation failed").
		WithField("errors", strings.Join(msgs, "; "))
}

// ExportSchema renders specs as a JSON Schema document (draft-07 subset).
func ExportSchema(specs map[string]*Spec) (string, error) {
	props := map[string]any{}
	required := []string{}
	for name, spec := range specs {
		entry := map[string]any{"description": spec.Name}
		switch spec.Type {
		case RuleInt:
			entry["type"] = "integer"
		case RuleFloat:
			entry["type"] = "number"
		case RuleBool:
			entry["type"] = "boolean"
		default:
			entry["type"] = "string"
		}
		if spec.HasRange {
			entry["minimum"] = spec.Min
			entry["maximum"] = spec.Max
		}
		if spec.HasEnum {
			entry["enum"] = spec.Enum
		}
		props[name] = entry
		if spec.Required {
			required = append(required, name)
		}
	}
	doc := map[string]any{
		"$schema":    "http://json-schema.org/draft-07/schema#",
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		doc["required"] = required
	}
	data, err := json.Marshal(doc)
	if err != nil {
		return "", err
	}
	return string(data), nil
}
