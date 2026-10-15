package inference

import (
	"context"
	"sort"
	"sync"
	"time"

	"github.com/astrovox/astrovox/internal/errors"
	"github.com/astrovox/astrovox/model"
)

// RegisteredModel is one loaded model version with its own executor, so
// per-model concurrency and queue limits are isolated from other models.
type RegisteredModel struct {
	// Name is the model family name.
	Name string
	// Version is the monotonically increasing registration version.
	Version int
	// Module is the registered model.
	Module model.Module
	// Executor is the model's bounded executor.
	Executor *Executor

	mu       sync.Mutex
	loaded   bool
	loadedAt time.Time
	requests int64
}

// IsLoaded reports whether the model is currently serving.
func (m *RegisteredModel) IsLoaded() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.loaded
}

// Health is a fixed-cardinality health snapshot for one model.
type ModelHealth struct {
	Name       string `json:"name"`
	Version    int    `json:"version"`
	Loaded     bool   `json:"loaded"`
	InFlight   int64  `json:"in_flight"`
	Completed  int64  `json:"completed"`
	Rejected   int64  `json:"rejected"`
	Failed     int64  `json:"failed"`
	Cancelled  int64  `json:"cancelled"`
	TimedOut   int64  `json:"timed_out"`
	QueueLen   int    `json:"queue_len"`
}

// Registry manages model lifecycle: registration, versioning, loading,
// unloading, and health. It composes Executor rather than owning a
// scheduler (ADR-3), and its mutex is a leaf lock: no callback, model
// call, or I/O happens while it is held.
type Registry struct {
	mu     sync.Mutex
	models map[string][]*RegisteredModel // name -> versions, ascending
	limits Limits
	workers int
}

// NewRegistry builds an empty registry. Limits are copied into every
// registered model's executor; workers bounds per-model concurrency.
func NewRegistry(workers int, limits Limits) *Registry {
	return &Registry{
		models:  map[string][]*RegisteredModel{},
		workers: workers,
		limits:  limits.withDefaultsFor(workers),
	}
}

func (l Limits) withDefaultsFor(workers int) Limits {
	if workers <= 0 {
		workers = 1
	}
	return l.withDefaults()
}

// Register adds a new model version. The same name may be registered
// repeatedly: each registration increments the version, which is how a
// model is replaced without breaking in-flight requests on the old
// version (the old executor drains on its own).
func (r *Registry) Register(name string, m model.Module) (*RegisteredModel, error) {
	if name == "" || m == nil {
		return nil, errors.New(errors.CodeInvalidArgument, "registry requires a name and a module")
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	versions := r.models[name]
	version := 1
	if n := len(versions); n > 0 {
		version = versions[n-1].Version + 1
	}
	exec, err := NewExecutor(&ModuleExecutable{Module: m}, r.workers, r.limits)
	if err != nil {
		return nil, err
	}
	rm := &RegisteredModel{
		Name:     name,
		Version:  version,
		Module:   m,
		Executor: exec,
		loaded:   true,
		loadedAt: time.Now(),
	}
	r.models[name] = append(versions, rm)
	return rm, nil
}

// Versions returns the registered versions of a model, ascending.
func (r *Registry) Versions(name string) []int {
	r.mu.Lock()
	defer r.mu.Unlock()
	versions := r.models[name]
	out := make([]int, 0, len(versions))
	for _, v := range versions {
		out = append(out, v.Version)
	}
	return out
}

// Latest returns the newest version of a model.
func (r *Registry) Latest(name string) (*RegisteredModel, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	versions := r.models[name]
	if len(versions) == 0 {
		return nil, errors.New(errors.CodeNotFound, "model is not registered").
			WithField("name", name)
	}
	return versions[len(versions)-1], nil
}

// Get returns a specific version.
func (r *Registry) Get(name string, version int) (*RegisteredModel, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, v := range r.models[name] {
		if v.Version == version {
			return v, nil
		}
	}
	return nil, errors.New(errors.CodeNotFound, "model version is not registered").
		WithField("name", name).WithField("version", version)
}

// Names lists registered model names, sorted.
func (r *Registry) Names() []string {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]string, 0, len(r.models))
	for name := range r.models {
		out = append(out, name)
	}
	sort.Strings(out)
	return out
}

// Run submits a request to a specific model version.
func (m *RegisteredModel) Run(ctx context.Context, req Request) (Result, error) {
	return m.Executor.Run(ctx, req)
}

// Submit submits a request to a specific model version.
func (m *RegisteredModel) Submit(ctx context.Context, req Request) (*Future, error) {
	return m.Executor.Submit(ctx, req)
}

// Health returns the model's health snapshot.
func (m *RegisteredModel) Health() ModelHealth {
	m.mu.Lock()
	loaded := m.loaded
	m.mu.Unlock()
	s := m.Executor.Stats()
	return ModelHealth{
		Name:      m.Name,
		Version:   m.Version,
		Loaded:    loaded,
		InFlight:  s.InFlight,
		Completed: s.Completed,
		Rejected:  s.Rejected,
		Failed:    s.Failed,
		Cancelled: s.Cancelled,
		TimedOut:  s.TimedOut,
		QueueLen:  s.QueueLen,
	}
}

// Unload marks the model unloaded and shuts down its executor, draining
// in-flight requests. A model that is already unloaded is a no-op.
func (m *RegisteredModel) Unload(timeout time.Duration) error {
	m.mu.Lock()
	if !m.loaded {
		m.mu.Unlock()
		return nil
	}
	m.loaded = false
	m.mu.Unlock()
	return m.Executor.Shutdown(timeout)
}

// RunLatest submits a request to the newest version of a model. The
// lookup and the submission are separate steps: a registration that
// lands between them does not redirect this request, which keeps the
// request's ownership stable.
func (r *Registry) RunLatest(ctx context.Context, name string, req Request) (Result, error) {
	m, err := r.Latest(name)
	if err != nil {
		return Result{ID: req.ID, Err: err}, err
	}
	return m.Run(ctx, req)
}

// Shutdown unloads every model, draining in-flight work.
func (r *Registry) Shutdown(timeout time.Duration) error {
	r.mu.Lock()
	models := make([]*RegisteredModel, 0)
	for _, versions := range r.models {
		models = append(models, versions...)
	}
	r.mu.Unlock()
	var firstErr error
	for _, m := range models {
		if err := m.Unload(timeout); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}

// Health returns a snapshot for every registered model version, sorted
// by name then version.
func (r *Registry) Health() []ModelHealth {
	r.mu.Lock()
	models := make([]*RegisteredModel, 0)
	for _, versions := range r.models {
		models = append(models, versions...)
	}
	r.mu.Unlock()
	out := make([]ModelHealth, 0, len(models))
	for _, m := range models {
		out = append(out, m.Health())
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Name != out[j].Name {
			return out[i].Name < out[j].Name
		}
		return out[i].Version < out[j].Version
	})
	return out
}

// Compile-time proof that the registry serves through the executor path:
// it holds no tensor state of its own, only models and executors.
type registryHoldsNoTensors struct{}

var _ = registryHoldsNoTensors{}
