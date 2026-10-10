// Package sandbox provides a safe execution sandbox for untrusted
// plugin code, with resource limits, capability checks, and an
// isolated execution environment.
package sandbox

import (
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"
)

// Capability identifies a permission a plugin can request.
type Capability int

const (
	CapFileRead Capability = iota
	CapFileWrite
	CapNetwork
	CapExec
	CapEnvRead
	CapClock
	CapMemory
)

func (c Capability) String() string {
	switch c {
	case CapFileRead:
		return "file.read"
	case CapFileWrite:
		return "file.write"
	case CapNetwork:
		return "network"
	case CapExec:
		return "exec"
	case CapEnvRead:
		return "env.read"
	case CapClock:
		return "clock"
	case CapMemory:
		return "memory"
	default:
		return "unknown"
	}
}

// CapabilitySet is a set of capabilities.
type CapabilitySet map[Capability]bool

// Grant grants a capability.
func (s CapabilitySet) Grant(c Capability) { s[c] = true }

// Revoke revokes a capability.
func (s CapabilitySet) Revoke(c Capability) { delete(s, c) }

// Has reports whether a capability is granted.
func (s CapabilitySet) Has(c Capability) bool { return s[c] }

// ResourceLimits bounds the resources a sandboxed task may use.
type ResourceLimits struct {
	MaxMemoryBytes int64
	MaxCPUTimeMs   int64
	MaxWallTimeMs  int64
	MaxOpenFiles   int
	MaxThreads     int
	MaxOutputBytes int64
	AllowNetwork   bool
}

// DefaultLimits returns conservative default limits.
func DefaultLimits() ResourceLimits {
	return ResourceLimits{
		MaxMemoryBytes: 64 * 1024 * 1024,
		MaxCPUTimeMs:   5000,
		MaxWallTimeMs:  10000,
		MaxOpenFiles:   16,
		MaxThreads:     4,
		MaxOutputBytes: 1024 * 1024,
		AllowNetwork:   false,
	}
}

// SandboxViolation describes a policy violation.
type SandboxViolation struct {
	Kind     string
	Resource string
	Detail   string
	Time     time.Time
}

// ViolationError is returned when a sandbox limit is exceeded.
type ViolationError struct {
	Violation SandboxViolation
}

func (e *ViolationError) Error() string {
	return fmt.Sprintf("sandbox violation: %s (%s): %s",
		e.Violation.Kind, e.Violation.Resource, e.Violation.Detail)
}

// Task is a unit of sandboxed work.
type Task interface {
	Name() string
	Run(env *Environment) error
}

// Environment is the sandboxed execution context handed to tasks.
type Environment struct {
	capabilities CapabilitySet
	limits       ResourceLimits
	caps         CapabilitySet
	started      time.Time
	memoryUsed   atomic.Int64
	outputBytes  atomic.Int64
	filesOpened  atomic.Int64
	filesClosed  atomic.Int64
	cpuTimeMs    atomic.Int64
}

// Capabilities returns the granted capabilities.
func (e *Environment) Capabilities() CapabilitySet { return e.caps }

// Require returns an error if the capability is not granted.
func (e *Environment) Require(c Capability) error {
	if !e.caps.Has(c) {
		return &ViolationError{SandboxViolation{
			Kind:     "capability",
			Resource: c.String(),
			Detail:   "capability not granted",
			Time:     time.Now(),
		}}
	}
	return nil
}

// MemoryUsed returns allocated bytes.
func (e *Environment) MemoryUsed() int64 { return e.memoryUsed.Load() }

// Allocate reserves memory, enforcing the memory limit.
func (e *Environment) Allocate(n int64) error {
	if err := e.Require(CapMemory); err != nil {
		return err
	}
	used := e.memoryUsed.Add(n)
	if used > e.limits.MaxMemoryBytes {
		return &ViolationError{SandboxViolation{
			Kind:     "resource_limit",
			Resource: "memory",
			Detail:   fmt.Sprintf("%d bytes exceeds limit %d", used, e.limits.MaxMemoryBytes),
			Time:     time.Now(),
		}}
	}
	return nil
}

// Free releases memory.
func (e *Environment) Free(n int64) { e.memoryUsed.Add(-n) }

// OpenFile registers an open file descriptor.
func (e *Environment) OpenFile() error {
	open := e.filesOpened.Add(1) - e.filesClosed.Load()
	if int(open) > e.limits.MaxOpenFiles {
		e.filesOpened.Add(-1)
		return &ViolationError{SandboxViolation{
			Kind:     "resource_limit",
			Resource: "files",
			Detail:   fmt.Sprintf("%d open exceeds limit %d", open, e.limits.MaxOpenFiles),
			Time:     time.Now(),
		}}
	}
	return nil
}

// CloseFile registers a closed file descriptor.
func (e *Environment) CloseFile() { e.filesClosed.Add(1) }

// WriteOutput records output bytes, enforcing the output limit.
func (e *Environment) WriteOutput(data []byte) error {
	if err := e.Require(CapFileWrite); err != nil {
		return err
	}
	used := e.outputBytes.Add(int64(len(data)))
	if used > e.limits.MaxOutputBytes {
		return &ViolationError{SandboxViolation{
			Kind:     "resource_limit",
			Resource: "output",
			Detail:   "output limit exceeded",
			Time:     time.Now(),
		}}
	}
	return nil
}

// CPUTimeMs returns tracked CPU time.
func (e *Environment) CPUTimeMs() int64 { return e.cpuTimeMs.Load() }

// AddCPUTime records CPU time, enforcing the CPU limit.
func (e *Environment) AddCPUTime(ms int64) error {
	used := e.cpuTimeMs.Add(ms)
	if used > e.limits.MaxCPUTimeMs {
		return &ViolationError{SandboxViolation{
			Kind:     "resource_limit",
			Resource: "cpu",
			Detail:   fmt.Sprintf("%dms exceeds limit %dms", used, e.limits.MaxCPUTimeMs),
			Time:     time.Now(),
		}}
	}
	return nil
}

// Sandbox executes tasks under a policy.
type Sandbox struct {
	policy Policy
	stats  SandboxStats
	mu     sync.RWMutex
}

// Policy defines what a sandbox permits.
type Policy struct {
	Name         string
	Capabilities CapabilitySet
	Limits       ResourceLimits
}

// NewSandbox creates a sandbox from a policy.
func NewSandbox(policy Policy) *Sandbox {
	return &Sandbox{policy: policy}
}

// Policy returns the sandbox policy.
func (s *Sandbox) Policy() Policy { return s.policy }

// SandboxStats tracks sandbox statistics.
type SandboxStats struct {
	TasksRun    atomic.Int64
	TasksPassed atomic.Int64
	TasksFailed atomic.Int64
	Violations  atomic.Int64
	TotalTimeNs atomic.Int64
}

// Execute runs a task under the sandbox policy.
func (s *Sandbox) Execute(task Task) error {
	if task == nil {
		return errors.New("nil task")
	}
	s.stats.TasksRun.Add(1)

	caps := make(CapabilitySet, len(s.policy.Capabilities))
	for c, v := range s.policy.Capabilities {
		caps[c] = v
	}
	env := &Environment{
		caps:    caps,
		limits:  s.policy.Limits,
		started: time.Now(),
	}

	// Enforce wall time with a watchdog goroutine.
	done := make(chan error, 1)
	go func() {
		defer func() {
			if r := recover(); r != nil {
				done <- fmt.Errorf("sandboxed task panicked: %v", r)
			}
		}()
		done <- task.Run(env)
	}()

	var err error
	timer := time.NewTimer(time.Duration(s.policy.Limits.MaxWallTimeMs) * time.Millisecond)
	defer timer.Stop()
	select {
	case err = <-done:
	case <-timer.C:
		err = &ViolationError{SandboxViolation{
			Kind:     "resource_limit",
			Resource: "wall_time",
			Detail:   fmt.Sprintf("exceeded %dms", s.policy.Limits.MaxWallTimeMs),
			Time:     time.Now(),
		}}
		s.stats.Violations.Add(1)
	}

	s.stats.TotalTimeNs.Add(time.Since(env.started).Nanoseconds())
	if err != nil {
		s.stats.TasksFailed.Add(1)
		var ve *ViolationError
		if errors.As(err, &ve) {
			s.stats.Violations.Add(1)
		}
		return err
	}
	s.stats.TasksPassed.Add(1)
	return nil
}

// Stats returns sandbox statistics.
func (s *Sandbox) Stats() *SandboxStats { return &s.stats }

// SanitizeName returns a safe identifier or an error.
func SanitizeName(name string) (string, error) {
	if name == "" {
		return "", errors.New("empty name")
	}
	out := make([]byte, 0, len(name))
	for i := 0; i < len(name); i++ {
		c := name[i]
		switch {
		case c >= 'a' && c <= 'z', c >= 'A' && c <= 'Z', c >= '0' && c <= '9':
			out = append(out, c)
		case c == '-' || c == '_' || c == '.':
			if i == 0 {
				return "", errors.New("name must start with a letter")
			}
			out = append(out, c)
		default:
			return "", fmt.Errorf("invalid character %q in name", string(c))
		}
	}
	return string(out), nil
}

// SandboxManager manages multiple sandboxes.
type SandboxManager struct {
	mu        sync.RWMutex
	sandboxes map[string]*Sandbox
}

// NewSandboxManager creates a manager.
func NewSandboxManager() *SandboxManager {
	return &SandboxManager{sandboxes: make(map[string]*Sandbox)}
}

// Create registers a sandbox by name.
func (m *SandboxManager) Create(name string, policy Policy) (*Sandbox, error) {
	safe, err := SanitizeName(name)
	if err != nil {
		return nil, err
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.sandboxes[safe]; ok {
		return nil, fmt.Errorf("sandbox %q already exists", safe)
	}
	sb := NewSandbox(policy)
	m.sandboxes[safe] = sb
	return sb, nil
}

// Get returns a sandbox by name.
func (m *SandboxManager) Get(name string) (*Sandbox, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	s, ok := m.sandboxes[name]
	return s, ok
}

// List returns sandbox names.
func (m *SandboxManager) List() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	names := make([]string, 0, len(m.sandboxes))
	for n := range m.sandboxes {
		names = append(names, n)
	}
	return names
}
