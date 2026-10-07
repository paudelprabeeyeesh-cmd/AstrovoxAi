// Package config implements a layered configuration loader supporting JSON and
// a minimal YAML subset, environment-variable overrides, validation, and
// hot-reload with atomic pointer swaps.
package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/internal/validator"
)

// Source identifies the origin layer of a configuration value.
type Source int

// Configuration precedence layers, lowest to highest.
const (
	SourceDefault Source = iota
	SourceFile
	SourceEnv
	SourceFlag
)

func (s Source) String() string {
	switch s {
	case SourceDefault:
		return "default"
	case SourceFile:
		return "file"
	case SourceEnv:
		return "env"
	case SourceFlag:
		return "flag"
	default:
		return "unknown"
	}
}

// Value is a configuration value tagged with its source layer.
type Value struct {
	Value  any     `json:"value"`
	Source Source  `json:"source"`
	Path   string  `json:"path"`
}

// Config is an immutable, typed configuration snapshot.
type Config struct {
	tree   map[string]any
	origin map[string]Source
	schema *Schema
	mu     sync.RWMutex
}

// Schema declares typed configuration keys with validation rules.
type Schema struct {
	Fields map[string]*FieldSpec `json:"fields"`
}

// FieldSpec describes one configuration key.
type FieldSpec struct {
	Type      validator.Rule `json:"type"`
	Required  bool           `json:"required"`
	Default   any            `json:"default"`
	Sensitive bool           `json:"sensitive"`
	Desc      string         `json:"desc"`
}

// New creates an empty configuration bound to a schema.
func New(schema *Schema) *Config {
	if schema == nil {
		schema = &Schema{Fields: map[string]*FieldSpec{}}
	}
	return &Config{
		tree:   map[string]any{},
		origin: map[string]Source{},
		schema: schema,
	}
}

// Load reads configuration from a JSON or YAML file, applies defaults, then
// environment overrides (prefix ASTROVOX_), and validates against the schema.
func Load(path string, schema *Schema) (*Config, error) {
	cfg := New(schema)
	if err := cfg.applyDefaults(); err != nil {
		return nil, err
	}
	if path != "" {
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, errors.Wrap(err, errors.CodeNotFound, "config file unreadable").WithField("path", path)
		}
		parsed, perr := ParseFile(path, data)
		if perr != nil {
			return nil, perr
		}
		if err := cfg.merge(SourceFile, "", parsed); err != nil {
			return nil, err
		}
	}
	if err := cfg.applyEnv("ASTROVOX_"); err != nil {
		return nil, err
	}
	if err := cfg.Validate(); err != nil {
		return nil, err
	}
	return cfg, nil
}

func (c *Config) applyDefaults() error {
	for key, spec := range c.schema.Fields {
		if spec.Default != nil {
			c.tree[key] = spec.Default
			c.origin[key] = SourceDefault
		}
	}
	return nil
}

func (c *Config) applyEnv(prefix string) error {
	prefix = strings.ToUpper(prefix)
	for _, kv := range os.Environ() {
		eq := strings.IndexByte(kv, '=')
		if eq < 0 {
			continue
		}
		name, val := kv[:eq], kv[eq+1:]
		if !strings.HasPrefix(name, prefix) {
			continue
		}
		key := strings.ToLower(strings.TrimPrefix(name, prefix))
		key = strings.ReplaceAll(key, "__", ".")
		key = strings.ReplaceAll(key, "_", ".")
		typed, err := coerce(val, c.schema.Fields[key])
		if err != nil {
			return errors.Wrap(err, errors.CodeInvalidArgument, "environment value invalid").
				WithField("key", key)
		}
		c.tree[key] = typed
		c.origin[key] = SourceEnv
	}
	return nil
}

func coerce(raw string, spec *FieldSpec) (any, error) {
	if spec != nil {
		switch spec.Type {
		case validator.RuleInt:
			n, err := strconv.ParseInt(raw, 10, 64)
			if err != nil {
				return nil, err
			}
			return n, nil
		case validator.RuleFloat:
			f, err := strconv.ParseFloat(raw, 64)
			if err != nil {
				return nil, err
			}
			return f, nil
		case validator.RuleBool:
			b, err := strconv.ParseBool(raw)
			if err != nil {
				return nil, err
			}
			return b, nil
		}
	}
	if raw == "true" || raw == "false" {
		b, err := strconv.ParseBool(raw)
		if err == nil {
			return b, nil
		}
	}
	if n, err := strconv.ParseInt(raw, 10, 64); err == nil {
		return n, nil
	}
	if f, err := strconv.ParseFloat(raw, 64); err == nil {
		return f, nil
	}
	return raw, nil
}

// ParseFile parses JSON or YAML configuration bytes based on the file extension.
func ParseFile(path string, data []byte) (map[string]any, error) {
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".json":
		var out map[string]any
		if err := json.Unmarshal(data, &out); err != nil {
			return nil, errors.Wrap(err, errors.CodeCorruptData, "config JSON parse failed")
		}
		return out, nil
	case ".yaml", ".yml":
		out, err := ParseYAML(data)
		if err != nil {
			return nil, err
		}
		return out, nil
	default:
		var out map[string]any
		if jerr := json.Unmarshal(data, &out); jerr == nil {
			return out, nil
		}
		parsed, yerr := ParseYAML(data)
		if yerr != nil {
			return nil, errors.New(errors.CodeCorruptData, "unsupported config file extension").
				WithField("path", path)
		}
		return parsed, nil
	}
}

// ParseYAML parses a minimal YAML subset: nested maps by indentation,
// scalar lists with "- " prefixes, and scalar values (string, int,
// float, bool, null).
func ParseYAML(data []byte) (map[string]any, error) {
	lines := strings.Split(string(data), "\n")
	type frame struct {
		indent  int
		m       map[string]any
		lastKey string
	}
	root := map[string]any{}
	stack := []frame{{indent: -1, m: root}}
	for _, raw := range lines {
		line := strings.TrimRight(raw, " \t\r")
		if strings.TrimSpace(line) == "" || strings.HasPrefix(strings.TrimSpace(line), "#") {
			continue
		}
		indent := len(line) - len(strings.TrimLeft(line, " "))
		trimmed := strings.TrimSpace(line)
		for len(stack) > 1 && indent <= stack[len(stack)-1].indent {
			stack = stack[:len(stack)-1]
		}
		parent := &stack[len(stack)-1]
		if strings.HasPrefix(trimmed, "- ") {
			if parent.lastKey == "" {
				return nil, errors.New(errors.CodeCorruptData, "list item without key").
					WithField("line", trimmed)
			}
			var list []any
			if existing, ok := parent.m[parent.lastKey].([]any); ok {
				list = existing
			}
			list = append(list, parseScalar(strings.TrimSpace(trimmed[2:])))
			parent.m[parent.lastKey] = list
			continue
		}
		colon := strings.Index(trimmed, ":")
		if colon < 0 {
			return nil, errors.New(errors.CodeCorruptData, "malformed YAML line").
				WithField("line", trimmed)
		}
		key := strings.TrimSpace(trimmed[:colon])
		val := strings.TrimSpace(trimmed[colon+1:])
		if val == "" {
			child := map[string]any{}
			parent.m[key] = child
			stack = append(stack, frame{indent: indent, m: child})
			continue
		}
		parent.m[key] = parseScalar(val)
		parent.lastKey = key
	}
	return root, nil
}

func parseScalar(s string) any {
	if len(s) >= 2 && (s[0] == '"' && s[len(s)-1] == '"') {
		return s[1 : len(s)-1]
	}
	if s == "null" || s == "~" || s == "" {
		return nil
	}
	if s == "true" {
		return true
	}
	if s == "false" {
		return false
	}
	if n, err := strconv.ParseInt(s, 10, 64); err == nil {
		return n
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return f
	}
	return s
}

func (c *Config) merge(src Source, prefix string, m map[string]any) error {
	for k, v := range m {
		key := k
		if prefix != "" {
			key = prefix + "." + k
		}
		if sub, ok := v.(map[string]any); ok {
			if err := c.merge(src, key, sub); err != nil {
				return err
			}
			continue
		}
		if cur, exists := c.origin[key]; exists && cur >= src {
			continue
		}
		c.tree[key] = v
		c.origin[key] = src
	}
	return nil
}

// Get returns the value at a dotted path, or nil when absent.
func (c *Config) Get(path string) any {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.tree[path]
}

// GetString returns the string value at path or the fallback.
func (c *Config) GetString(path, fallback string) string {
	v, ok := c.Get(path).(string)
	if !ok {
		return fallback
	}
	return v
}

// GetInt returns the int value at path or the fallback.
func (c *Config) GetInt(path string, fallback int) int {
	switch v := c.Get(path).(type) {
	case int:
		return v
	case int64:
		return int(v)
	case float64:
		return int(v)
	default:
		return fallback
	}
}

// GetFloat returns the float64 value at path or the fallback.
func (c *Config) GetFloat(path string, fallback float64) float64 {
	switch v := c.Get(path).(type) {
	case float64:
		return v
	case int:
		return float64(v)
	case int64:
		return float64(v)
	default:
		return fallback
	}
}

// GetBool returns the bool value at path or the fallback.
func (c *Config) GetBool(path string, fallback bool) bool {
	v, ok := c.Get(path).(bool)
	if !ok {
		return fallback
	}
	return v
}

// SourceOf returns the precedence layer that supplied the key.
func (c *Config) SourceOf(path string) Source {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.origin[path]
}

// Set overrides a configuration value at the flag layer (highest precedence).
func (c *Config) Set(path string, value any) {
	c.mu.Lock()
	c.tree[path] = value
	c.origin[path] = SourceFlag
	c.mu.Unlock()
}

// Snapshot returns a copy of the configuration tree with sensitive values redacted.
func (c *Config) Snapshot() map[string]Value {
	c.mu.RLock()
	defer c.mu.RUnlock()
	out := make(map[string]Value, len(c.tree))
	for k, v := range c.tree {
		val := Value{Source: c.origin[k], Path: k}
		if spec := c.schema.Fields[k]; spec != nil && spec.Sensitive {
			val.Value = "***redacted***"
		} else {
			val.Value = v
		}
		out[k] = val
	}
	return out
}

// Keys returns the sorted configuration keys.
func (c *Config) Keys() []string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	keys := make([]string, 0, len(c.tree))
	for k := range c.tree {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// Validate checks the configuration against its schema.
func (c *Config) Validate() error {
	c.mu.RLock()
	defer c.mu.RUnlock()
	var errs []string
	for key, spec := range c.schema.Fields {
		v, exists := c.tree[key]
		if !exists {
			if spec.Required {
				errs = append(errs, fmt.Sprintf("missing required key %q", key))
			}
			continue
		}
		if spec.Type != 0 {
			if err := validator.Check(fmt.Sprint(v), spec.Type, key); err != nil {
				errs = append(errs, err.Error())
			}
		}
	}
	if len(errs) > 0 {
		return errors.New(errors.CodeInvalidArgument, "configuration invalid").
			WithField("errors", strings.Join(errs, "; "))
	}
	return nil
}

// ErrNoConfig signals that no configuration source was provided.
var ErrNoConfig = errors.New(errors.CodeNotFound, "no configuration source")

// Watch subscribes to file changes and atomically reloads the configuration.
// The returned cancel function stops the watcher.
func Watch(path string, schema *Schema, onChange func(*Config), pollInterval int64) (func(), error) {
	cfg, err := Load(path, schema)
	if err != nil {
		return nil, err
	}
	current := atomic.Pointer[Config]{}
	current.Store(cfg)
	stop := make(chan struct{})
	done := make(chan struct{})
	go func() {
		defer close(done)
		ticker := timeTicker(pollInterval)
		defer ticker.Stop()
		for {
			select {
			case <-stop:
				return
			case <-ticker.C:
				fresh, err := Load(path, schema)
				if err != nil {
					continue
				}
				current.Store(fresh)
				onChange(fresh)
			}
		}
	}()
	return func() {
		close(stop)
		<-done
	}, nil
}
