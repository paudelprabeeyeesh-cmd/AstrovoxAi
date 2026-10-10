// Package checkpoint provides asynchronous parameter checkpointing and
// synchronization for distributed training.
package checkpoint

import (
	"context"
	"errors"
	"fmt"
	"math"
	"sync"
	"sync/atomic"
	"time"
)

// Errors returned by the checkpoint coordinator.
var (
	ErrNoSnapshot    = errors.New("no snapshot available")
	ErrVersionBehind = errors.New("local version is behind remote")
	ErrShardMissing  = errors.New("requested shard not found")
)

// Shard is a slice of parameters with its own version.
type Shard struct {
	Name    string
	Version int64
	Data    []float64
	Hash    uint64
}

// Snapshot is a complete model checkpoint at a version.
type Snapshot struct {
	Version   int64
	Timestamp time.Time
	Shards    map[string]*Shard
	Commit    string
}

// ShardNames returns the shard names in the snapshot.
func (s *Snapshot) ShardNames() []string {
	out := make([]string, 0, len(s.Shards))
	for n := range s.Shards {
		out = append(out, n)
	}
	return out
}

// ParamCount returns the total number of elements across shards.
func (s *Snapshot) ParamCount() int {
	total := 0
	for _, sh := range s.Shards {
		total += len(sh.Data)
	}
	return total
}

// Store persists snapshots.
type Store interface {
	Save(s *Snapshot) error
	Load(version int64) (*Snapshot, error)
	Latest() (*Snapshot, error)
	Versions() []int64
}

// MemoryStore is an in-memory snapshot store.
type MemoryStore struct {
	mu        sync.RWMutex
	snapshots map[int64]*Snapshot
	order     []int64
	maxKept   int
}

// NewMemoryStore creates a memory store keeping at most maxKept snapshots.
func NewMemoryStore(maxKept int) *MemoryStore {
	if maxKept <= 0 {
		maxKept = 8
	}
	return &MemoryStore{
		snapshots: make(map[int64]*Snapshot),
		maxKept:   maxKept,
	}
}

// Save stores a snapshot.
func (m *MemoryStore) Save(s *Snapshot) error {
	if s == nil {
		return errors.New("nil snapshot")
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.snapshots[s.Version]; !ok {
		m.order = append(m.order, s.Version)
	}
	m.snapshots[s.Version] = s
	// Drop oldest beyond the retention limit.
	if len(m.order) > m.maxKept {
		for len(m.order) > m.maxKept {
			old := m.order[0]
			delete(m.snapshots, old)
			m.order = m.order[1:]
		}
	}
	return nil
}

// Load returns a snapshot by version.
func (m *MemoryStore) Load(version int64) (*Snapshot, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	s, ok := m.snapshots[version]
	if !ok {
		return nil, fmt.Errorf("%w: version %d", ErrNoSnapshot, version)
	}
	return s, nil
}

// Latest returns the newest snapshot.
func (m *MemoryStore) Latest() (*Snapshot, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if len(m.order) == 0 {
		return nil, ErrNoSnapshot
	}
	return m.snapshots[m.order[len(m.order)-1]], nil
}

// Versions returns the stored versions in ascending order.
func (m *MemoryStore) Versions() []int64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return append([]int64(nil), m.order...)
}

// Count returns the number of stored snapshots.
func (m *MemoryStore) Count() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.snapshots)
}

// Coordinator saves and syncs checkpoints.
type Coordinator struct {
	store      Store
	mu         sync.RWMutex
	localShard map[string]*Shard
	numShards  int
	stats      Stats
	interval   time.Duration
}

// Stats tracks checkpoint statistics.
type Stats struct {
	Saved      atomic.Int64
	Synced     atomic.Int64
	AsyncSaves atomic.Int64
	SyncErrors atomic.Int64
}

// NewCoordinator creates a checkpoint coordinator.
func NewCoordinator(store Store, numShards int) *Coordinator {
	return &Coordinator{
		store:      store,
		localShard: make(map[string]*Shard),
		numShards:  numShards,
	}
}

// PutShard records a local shard for the next snapshot.
func (c *Coordinator) PutShard(sh *Shard) error {
	if sh == nil || sh.Name == "" {
		return errors.New("invalid shard")
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	sh.Hash = hashFloats(sh.Data)
	c.localShard[sh.Name] = sh
	return nil
}

// ShardCount returns the number of locally recorded shards.
func (c *Coordinator) ShardCount() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.localShard)
}

// Save writes a new snapshot and returns it.
func (c *Coordinator) Save(commit string) (*Snapshot, error) {
	c.mu.RLock()
	latest, _ := c.store.Latest()
	next := int64(1)
	if latest != nil {
		next = latest.Version + 1
	}
	snap := &Snapshot{
		Version:   next,
		Timestamp: time.Now(),
		Shards:    make(map[string]*Shard, len(c.localShard)),
		Commit:    commit,
	}
	for n, sh := range c.localShard {
		cp := &Shard{Name: sh.Name, Version: next, Data: append([]float64(nil), sh.Data...), Hash: sh.Hash}
		snap.Shards[n] = cp
	}
	c.mu.RUnlock()

	if err := c.store.Save(snap); err != nil {
		return nil, err
	}
	c.stats.Saved.Add(1)
	return snap, nil
}

// SaveAsync saves a snapshot in the background.
func (c *Coordinator) SaveAsync(commit string) <-chan error {
	errCh := make(chan error, 1)
	c.stats.AsyncSaves.Add(1)
	go func() {
		_, err := c.Save(commit)
		errCh <- err
	}()
	return errCh
}

// Sync pulls the latest snapshot and applies shards by callback.
func (c *Coordinator) Sync(ctx context.Context, apply func(sh *Shard) error) (*Snapshot, error) {
	latest, err := c.store.Latest()
	if err != nil {
		return nil, err
	}
	for name, sh := range latest.Shards {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}
		if apply == nil {
			continue
		}
		if err := apply(&Shard{
			Name:    name,
			Version: sh.Version,
			Data:    append([]float64(nil), sh.Data...),
			Hash:    sh.Hash,
		}); err != nil {
			c.stats.SyncErrors.Add(1)
			return nil, err
		}
	}
	c.stats.Synced.Add(1)
	return latest, nil
}

// Diff returns the shards that differ between two versions.
func (c *Coordinator) Diff(localVersion int64) ([]string, error) {
	latest, err := c.store.Latest()
	if err != nil {
		return nil, err
	}
	c.mu.RLock()
	defer c.mu.RUnlock()
	var changed []string
	for name, sh := range latest.Shards {
		local, ok := c.localShard[name]
		if !ok || local.Version < sh.Version || local.Hash != sh.Hash {
			changed = append(changed, name)
		}
	}
	return changed, nil
}

// Verify checks that all shard hashes match their data.
func (c *Coordinator) Verify() bool {
	snap, err := c.store.Latest()
	if err != nil {
		return false
	}
	for _, sh := range snap.Shards {
		if hashFloats(sh.Data) != sh.Hash {
			return false
		}
	}
	return true
}

// GetShard returns a shard from the latest snapshot.
func (c *Coordinator) GetShard(name string) (*Shard, error) {
	latest, err := c.store.Latest()
	if err != nil {
		return nil, err
	}
	sh, ok := latest.Shards[name]
	if !ok {
		return nil, fmt.Errorf("%w: %s", ErrShardMissing, name)
	}
	return sh, nil
}

// Stats returns checkpoint statistics.
func (c *Coordinator) Stats() *Stats { return &c.stats }

// hashFloats is an FNV-1a hash over float64 bits.
func hashFloats(v []float64) uint64 {
	const (
		offset = 14695981039346656037
		prime  = 1099511628211
	)
	h := uint64(offset)
	for _, x := range v {
		bits := floatBits(x)
		for i := 0; i < 8; i++ {
			h ^= (bits >> (8 * uint(i))) & 0xff
			h *= prime
		}
	}
	return h
}

func floatBits(f float64) uint64 {
	return math.Float64bits(f)
}
