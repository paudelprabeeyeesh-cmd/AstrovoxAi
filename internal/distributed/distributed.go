// Package distributed provides distributed training components.
package distributed

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/astrovox/astrovox/tensor"
)

var (
	ErrNotInitialized = errors.New("distributed not initialized")
	ErrRankOutOfRange = errors.New("rank out of range")
	ErrGroupNotFound  = errors.New("process group not found")
)

// BackendType represents the communication backend.
type BackendType int

const (
	BackendGloo BackendType = iota
	BackendNCCL
	BackendMPI
	BackendUCC
)

// ProcessGroup represents a group of processes for collective communication.
type ProcessGroup struct {
	rank        int
	worldSize   int
	backend     BackendType
	ranks       []int
	groupName   string
	store       Store
	mu          sync.RWMutex
	collectives map[string]*CollectiveOp
}

// Store provides key-value storage for rendezvous.
type Store interface {
	Set(key string, value []byte) error
	Get(key string) ([]byte, error)
	Wait(keys []string, timeout time.Duration) error
}

// CollectiveOp represents an ongoing collective operation.
type CollectiveOp struct {
	opType     CollectiveType
	input      []byte
	output     []byte
	root       int
	done       chan error
	completion func([]byte) error
}

type CollectiveType int

const (
	CollectiveAllReduce CollectiveType = iota
	CollectiveAllGather
	CollectiveBroadcast
	CollectiveReduce
	CollectiveReduceScatter
	CollectiveAllToAll
	CollectiveBarrier
)

// NewProcessGroup creates a new process group.
func NewProcessGroup(rank, worldSize int, backend BackendType, store Store) *ProcessGroup {
	return &ProcessGroup{
		rank:        rank,
		worldSize:   worldSize,
		backend:     backend,
		ranks:       make([]int, worldSize),
		collectives: make(map[string]*CollectiveOp),
		store:       store,
	}
}

// Rank returns the rank of this process in the group.
func (pg *ProcessGroup) Rank() int {
	return pg.rank
}

// WorldSize returns the total number of processes in the group.
func (pg *ProcessGroup) WorldSize() int {
	return pg.worldSize
}

// AllReduce performs an all-reduce operation.
func (pg *ProcessGroup) AllReduce(ctx context.Context, input *tensor.Tensor, op ReduceOp) (*tensor.Tensor, error) {
	return pg.collective(ctx, CollectiveAllReduce, input, op, -1)
}

// AllGather performs an all-gather operation.
func (pg *ProcessGroup) AllGather(ctx context.Context, input *tensor.Tensor) ([]*tensor.Tensor, error) {
	return nil, errors.New("not implemented")
}

// Broadcast performs a broadcast operation.
func (pg *ProcessGroup) Broadcast(ctx context.Context, input *tensor.Tensor, root int) (*tensor.Tensor, error) {
	return pg.collective(ctx, CollectiveBroadcast, input, ReduceOpSum, root)
}

// Reduce performs a reduce operation.
func (pg *ProcessGroup) Reduce(ctx context.Context, input *tensor.Tensor, root int, op ReduceOp) (*tensor.Tensor, error) {
	return pg.collective(ctx, CollectiveReduce, input, op, root)
}

// Barrier synchronizes all processes in the group.
func (pg *ProcessGroup) Barrier(ctx context.Context) error {
	_, err := pg.collective(ctx, CollectiveBarrier, nil, ReduceOpSum, -1)
	return err
}

func (pg *ProcessGroup) collective(ctx context.Context, opType CollectiveType, input *tensor.Tensor, op ReduceOp, root int) (*tensor.Tensor, error) {
	// Simplified implementation - in practice would use actual backend
	// For now, just return input for single-process testing
	if pg.worldSize == 1 {
		return input, nil
	}

	// Would implement actual collective communication here
	return input, errors.New("distributed collectives not fully implemented")
}

// ReduceOp represents reduction operations.
type ReduceOp int

const (
	ReduceOpSum ReduceOp = iota
	ReduceOpAvg
	ReduceOpMin
	ReduceOpMax
	ReduceOpProd
)

// InitProcessGroup initializes the default process group.
func InitProcessGroup(backend BackendType, initMethod string, worldSize, rank int, timeout time.Duration) (*ProcessGroup, error) {
	store := NewTCPStore(initMethod, worldSize, timeout)
	return NewProcessGroup(rank, worldSize, backend, store), nil
}

// DestroyProcessGroup cleans up the process group.
func DestroyProcessGroup(pg *ProcessGroup) error {
	return nil
}

// TCPStore implements Store using TCP.
type TCPStore struct {
	addr      string
	worldSize int
	timeout   time.Duration
	data      map[string][]byte
	mu        sync.RWMutex
	notify    map[string][]chan struct{}
}

func NewTCPStore(addr string, worldSize int, timeout time.Duration) *TCPStore {
	return &TCPStore{
		addr:      addr,
		worldSize: worldSize,
		timeout:   timeout,
		data:      make(map[string][]byte),
		notify:    make(map[string][]chan struct{}),
	}
}

func (s *TCPStore) Set(key string, value []byte) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.data[key] = value
	if chans, ok := s.notify[key]; ok {
		for _, ch := range chans {
			close(ch)
		}
		delete(s.notify, key)
	}
	return nil
}

func (s *TCPStore) Get(key string) ([]byte, error) {
	s.mu.RLock()
	val, ok := s.data[key]
	s.mu.RUnlock()
	if ok {
		return val, nil
	}
	// Wait for key
	ch := make(chan struct{}, 1)
	s.mu.Lock()
	s.notify[key] = append(s.notify[key], ch)
	s.mu.Unlock()
	select {
	case <-ch:
		s.mu.RLock()
		val = s.data[key]
		s.mu.RUnlock()
		return val, nil
	case <-time.After(s.timeout):
		return nil, errors.New("timeout waiting for key")
	}
}

func (s *TCPStore) Wait(keys []string, timeout time.Duration) error {
	for _, key := range keys {
		_, err := s.Get(key)
		if err != nil {
			return err
		}
	}
	return nil
}

// DistributedContext holds distributed training state.
type DistributedContext struct {
	rank         int
	worldSize    int
	defaultGroup *ProcessGroup
	groups       map[string]*ProcessGroup
	groupMu      sync.RWMutex
	initialized  bool
	initOnce     sync.Once
}

var defaultContext = &DistributedContext{
	groups: make(map[string]*ProcessGroup),
}

// Init initializes the default distributed context.
func Init(backend BackendType, initMethod string, worldSize, rank int, timeout time.Duration) error {
	var initErr error
	defaultContext.initOnce.Do(func() {
		pg, err := InitProcessGroup(backend, initMethod, worldSize, rank, timeout)
		if err != nil {
			initErr = err
			return
		}
		defaultContext.defaultGroup = pg
		defaultContext.rank = rank
		defaultContext.worldSize = worldSize
		defaultContext.groups["default"] = pg
		defaultContext.initialized = true
	})
	return initErr
}

// GetDefaultGroup returns the default process group.
func GetDefaultGroup() *ProcessGroup {
	if !defaultContext.initialized {
		return nil
	}
	return defaultContext.defaultGroup
}

// NewGroup creates a new process group with a subset of ranks.
func NewGroup(ranks []int, backend BackendType) (*ProcessGroup, error) {
	if !defaultContext.initialized {
		return nil, ErrNotInitialized
	}

	// Validate ranks
	for _, r := range ranks {
		if r < 0 || r >= defaultContext.worldSize {
			return nil, ErrRankOutOfRange
		}
	}

	groupName := fmt.Sprintf("group_%d", len(defaultContext.groups))
	store := NewTCPStore("inproc://"+groupName, len(ranks), 30*time.Second)

	// Find this process's rank in the new group
	newRank := -1
	for i, r := range ranks {
		if r == defaultContext.rank {
			newRank = i
			break
		}
	}
	if newRank == -1 {
		return nil, ErrRankOutOfRange
	}

	pg := NewProcessGroup(newRank, len(ranks), backend, store)
	defaultContext.groupMu.Lock()
	defaultContext.groups[groupName] = pg
	defaultContext.groupMu.Unlock()

	return pg, nil
}

// GetGroup retrieves a named process group.
func GetGroup(name string) (*ProcessGroup, error) {
	defaultContext.groupMu.RLock()
	defer defaultContext.groupMu.RUnlock()
	pg, ok := defaultContext.groups[name]
	if !ok {
		return nil, ErrGroupNotFound
	}
	return pg, nil
}

// Rank returns the global rank.
func Rank() int {
	return defaultContext.rank
}

// WorldSize returns the global world size.
func WorldSize() int {
	return defaultContext.worldSize
}

// IsInitialized returns whether distributed is initialized.
func IsInitialized() bool {
	return defaultContext.initialized
}

// Barrier synchronizes all processes in the default group.
func Barrier(ctx context.Context) error {
	if defaultContext.defaultGroup == nil {
		return ErrNotInitialized
	}
	return defaultContext.defaultGroup.Barrier(ctx)
}

// AllReduce performs all-reduce on the default group.
func AllReduce(ctx context.Context, input *tensor.Tensor, op ReduceOp) (*tensor.Tensor, error) {
	if defaultContext.defaultGroup == nil {
		return nil, ErrNotInitialized
	}
	return defaultContext.defaultGroup.AllReduce(ctx, input, op)
}

// Broadcast performs broadcast on the default group.
func Broadcast(ctx context.Context, input *tensor.Tensor, root int) (*tensor.Tensor, error) {
	if defaultContext.defaultGroup == nil {
		return nil, ErrNotInitialized
	}
	return defaultContext.defaultGroup.Broadcast(ctx, input, root)
}

// Reduce performs reduce on the default group.
func Reduce(ctx context.Context, input *tensor.Tensor, root int, op ReduceOp) (*tensor.Tensor, error) {
	if defaultContext.defaultGroup == nil {
		return nil, ErrNotInitialized
	}
	return defaultContext.defaultGroup.Reduce(ctx, input, root, op)
}
