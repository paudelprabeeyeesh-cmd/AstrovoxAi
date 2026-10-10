// Package distributed provides RPC framework implementation.
package distributed

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"github.com/astrovox/astrovox/tensor"
)

var (
	ErrRPCNotInit     = errors.New("RPC not initialized")
	ErrRPCNotFound    = errors.New("RPC target not found")
	ErrRPCTimeout     = errors.New("RPC timeout")
	ErrRPCCancelled   = errors.New("RPC cancelled")
	ErrMethodNotFound = errors.New("RPC method not found")
	ErrInvalidArgs    = errors.New("invalid RPC arguments")
	ErrServerFull     = errors.New("RPC server full")
)

// RPCTensor wraps a tensor for RPC serialization.
type RPCTensor struct {
	Data  []float64 `json:"data"`
	Shape []int     `json:"shape"`
}

// NewRPCTensor creates an RPC tensor from a tensor.
func NewRPCTensor(t *tensor.Tensor) *RPCTensor {
	return &RPCTensor{
		Data:  t.Float64(),
		Shape: t.Shape().Dims(),
	}
}

// ToTensor converts an RPC tensor back to a tensor.
func (rt *RPCTensor) ToTensor() (*tensor.Tensor, error) {
	t, err := tensor.New(tensor.Float64, rt.Shape)
	if err != nil {
		return nil, err
	}
	copy(t.Float64(), rt.Data)
	return t, nil
}

// RPCFunction represents a remote callable function.
type RPCFunction func(ctx context.Context, args ...interface{}) (interface{}, error)

// RPCRequest represents an RPC request.
type RPCRequest struct {
	RequestID string        `json:"request_id"`
	Method    string        `json:"method"`
	Args      []interface{} `json:"args"`
	Target    string        `json:"target"`
	Timeout   time.Duration `json:"timeout"`
}

// RPCResponse represents an RPC response.
type RPCResponse struct {
	RequestID string      `json:"request_id"`
	Result    interface{} `json:"result,omitempty"`
	Error     string      `json:"error,omitempty"`
	OK        bool        `json:"ok"`
}

// RPCEndpoint represents a remote endpoint.
type RPCEndpoint struct {
	Name    string
	Address string
	Rank    int
	Group   string
}

// RPCConfig holds RPC configuration.
type RPCConfig struct {
	Backend         string // "tcp", "unix", "inproc"
	Address         string
	Timeout         time.Duration
	MaxConcurrent   int
	BufferSize      int
	CompressTensors bool
}

// RPCManager manages RPC connections and method registry.
type RPCManager struct {
	config    *RPCConfig
	rank      int
	worldSize int
	selfName  string

	mu          sync.RWMutex
	methods     map[string]RPCFunction
	endpoints   map[string]*RPCEndpoint
	connections map[string]*RPCConnection

	server *RPCServer
	client *RPCClient

	initialized atomic.Bool
	running     atomic.Bool

	stats RPCStats
}

// RPCStats tracks RPC statistics.
type RPCStats struct {
	TotalRequests  atomic.Int64
	TotalResponses atomic.Int64
	TotalErrors    atomic.Int64
	TotalTimeouts  atomic.Int64
	AvgLatencyMs   atomic.Int64
	BytesSent      atomic.Int64
	BytesReceived  atomic.Int64
}

// RPCConnection represents a connection to a remote endpoint.
type RPCConnection struct {
	endpoint *RPCEndpoint
	address  string
	conn     interface{} // Underlying connection
	mu       sync.Mutex
	pending  map[string]chan *RPCResponse
}

// NewRPCManager creates a new RPC manager.
func NewRPCManager(config *RPCConfig, rank, worldSize int) (*RPCManager, error) {
	if config == nil {
		config = &RPCConfig{
			Backend:       "inproc",
			Address:       "localhost:0",
			Timeout:       30 * time.Second,
			MaxConcurrent: 100,
			BufferSize:    1024,
		}
	}

	m := &RPCManager{
		config:      config,
		rank:        rank,
		worldSize:   worldSize,
		selfName:    fmt.Sprintf("worker_%d", rank),
		methods:     make(map[string]RPCFunction),
		endpoints:   make(map[string]*RPCEndpoint),
		connections: make(map[string]*RPCConnection),
	}

	return m, nil
}

// Init initializes the RPC manager.
func (m *RPCManager) Init(ctx context.Context) error {
	if m.initialized.Swap(true) {
		return nil
	}

	m.server = NewRPCServer(m)
	m.client = NewRPCClient(m)

	if err := m.server.Start(ctx); err != nil {
		return err
	}

	m.running.Store(true)
	return nil
}

// Shutdown shuts down the RPC manager.
func (m *RPCManager) Shutdown(ctx context.Context) error {
	if !m.initialized.Load() {
		return nil
	}
	m.running.Store(false)
	return m.server.Stop(ctx)
}

// RegisterMethod registers an RPC method.
func (m *RPCManager) RegisterMethod(name string, fn RPCFunction) error {
	if fn == nil {
		return ErrInvalidArgs
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.methods[name] = fn
	return nil
}

// GetMethod retrieves a registered method.
func (m *RPCManager) GetMethod(name string) (RPCFunction, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	fn, ok := m.methods[name]
	return fn, ok
}

// RegisterEndpoint registers a remote endpoint.
func (m *RPCManager) RegisterEndpoint(name, address string, rank int, group string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.endpoints[name] = &RPCEndpoint{
		Name:    name,
		Address: address,
		Rank:    rank,
		Group:   group,
	}
}

// GetEndpoint retrieves an endpoint.
func (m *RPCManager) GetEndpoint(name string) (*RPCEndpoint, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	ep, ok := m.endpoints[name]
	if !ok {
		return nil, ErrRPCNotFound
	}
	return ep, nil
}

// RPCServer handles incoming RPC requests.
type RPCServer struct {
	manager     *RPCManager
	listener    interface{} // net.Listener or similar
	mu          sync.Mutex
	handlers    map[string]RPCFunction
	activeConns atomic.Int64
	totalReqs   atomic.Int64
	shutdown    chan struct{}
}

// NewRPCServer creates a new RPC server.
func NewRPCServer(m *RPCManager) *RPCServer {
	return &RPCServer{
		manager:  m,
		handlers: m.methods,
		shutdown: make(chan struct{}),
	}
}

// Start starts the RPC server.
func (s *RPCServer) Start(ctx context.Context) error {
	// In production, would start TCP/Unix socket listener
	// For now, in-process only
	return nil
}

// Stop stops the RPC server.
func (s *RPCServer) Stop(ctx context.Context) error {
	close(s.shutdown)
	return nil
}

// HandleRequest processes an incoming RPC request.
func (s *RPCServer) HandleRequest(ctx context.Context, req *RPCRequest) *RPCResponse {
	s.totalReqs.Add(1)

	method, ok := s.manager.GetMethod(req.Method)
	if !ok {
		return &RPCResponse{
			RequestID: req.RequestID,
			Error:     fmt.Sprintf("method not found: %s", req.Method),
			OK:        false,
		}
	}

	// Apply timeout
	if req.Timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, req.Timeout)
		defer cancel()
	}

	// Execute method
	result, err := method(ctx, req.Args...)
	if err != nil {
		return &RPCResponse{
			RequestID: req.RequestID,
			Error:     err.Error(),
			OK:        false,
		}
	}

	return &RPCResponse{
		RequestID: req.RequestID,
		Result:    result,
		OK:        true,
	}
}

// RPCClient sends RPC requests to remote endpoints.
type RPCClient struct {
	manager *RPCManager
	mu      sync.Mutex
	pending map[string]*PendingRequest
}

// PendingRequest tracks an in-flight request.
type PendingRequest struct {
	RequestID string
	Target    string
	Method    string
	Response  chan *RPCResponse
	StartTime time.Time
}

// NewRPCClient creates a new RPC client.
func NewRPCClient(m *RPCManager) *RPCClient {
	return &RPCClient{
		manager: m,
		pending: make(map[string]*PendingRequest),
	}
}

// Call makes an RPC call to a remote endpoint.
func (c *RPCClient) Call(ctx context.Context, target, method string, args ...interface{}) (interface{}, error) {
	// Get endpoint
	endpoint, err := c.manager.GetEndpoint(target)
	if err != nil {
		return nil, err
	}

	// Create request
	reqID := fmt.Sprintf("req_%d_%d", time.Now().UnixNano(), c.manager.stats.TotalRequests.Add(1))
	req := &RPCRequest{
		RequestID: reqID,
		Method:    method,
		Args:      args,
		Target:    target,
		Timeout:   c.manager.config.Timeout,
	}

	// Track pending request
	pending := &PendingRequest{
		RequestID: reqID,
		Target:    target,
		Method:    method,
		Response:  make(chan *RPCResponse, 1),
		StartTime: time.Now(),
	}
	c.mu.Lock()
	c.pending[reqID] = pending
	c.mu.Unlock()

	defer func() {
		c.mu.Lock()
		delete(c.pending, reqID)
		c.mu.Unlock()
	}()

	// Send request (in-process simulation)
	// In production, would send over network
	resp := c.simulateRequest(ctx, endpoint, req)

	select {
	case <-ctx.Done():
		c.manager.stats.TotalTimeouts.Add(1)
		return nil, ErrRPCTimeout
	case response := <-resp:
		if !response.OK {
			c.manager.stats.TotalErrors.Add(1)
			return nil, errors.New(response.Error)
		}

		// Update latency stats
		latencyMs := time.Since(pending.StartTime).Milliseconds()
		c.manager.stats.TotalResponses.Add(1)
		// Simple moving average
		oldAvg := c.manager.stats.AvgLatencyMs.Load()
		newAvg := (oldAvg + latencyMs) / 2
		c.manager.stats.AvgLatencyMs.Store(newAvg)

		return response.Result, nil
	}
}

// simulateRequest simulates an RPC request for in-process testing.
func (c *RPCClient) simulateRequest(ctx context.Context, endpoint *RPCEndpoint, req *RPCRequest) chan *RPCResponse {
	respChan := make(chan *RPCResponse, 1)

	go func() {
		// Simulate network delay
		select {
		case <-time.After(1 * time.Millisecond):
		case <-ctx.Done():
			respChan <- &RPCResponse{RequestID: req.RequestID, Error: "cancelled", OK: false}
			return
		}

		// Execute locally (simulation)
		method, ok := c.manager.GetMethod(req.Method)
		if !ok {
			respChan <- &RPCResponse{RequestID: req.RequestID, Error: "method not found", OK: false}
			return
		}

		result, err := method(ctx, req.Args...)
		if err != nil {
			respChan <- &RPCResponse{RequestID: req.RequestID, Error: err.Error(), OK: false}
			return
		}

		respChan <- &RPCResponse{RequestID: req.RequestID, Result: result, OK: true}
	}()

	return respChan
}

// AsyncCall makes an asynchronous RPC call.
func (c *RPCClient) AsyncCall(ctx context.Context, target, method string, args ...interface{}) (*RPCFuture, error) {
	future := &RPCFuture{
		resultChan: make(chan interface{}, 1),
		errChan:    make(chan error, 1),
	}

	go func() {
		result, err := c.Call(ctx, target, method, args...)
		if err != nil {
			future.errChan <- err
			return
		}
		future.resultChan <- result
	}()

	return future, nil
}

// RPCFuture represents a pending RPC result.
type RPCFuture struct {
	resultChan chan interface{}
	errChan    chan error
}

// Wait waits for the RPC result.
func (f *RPCFuture) Wait() (interface{}, error) {
	select {
	case result := <-f.resultChan:
		return result, nil
	case err := <-f.errChan:
		return nil, err
	}
}

// WaitWithTimeout waits for the RPC result with a timeout.
func (f *RPCFuture) WaitWithTimeout(timeout time.Duration) (interface{}, error) {
	select {
	case result := <-f.resultChan:
		return result, nil
	case err := <-f.errChan:
		return nil, err
	case <-time.After(timeout):
		return nil, ErrRPCTimeout
	}
}

// RemoteExecutor provides remote execution of operations.
type RemoteExecutor struct {
	rpc *RPCManager
}

// NewRemoteExecutor creates a remote executor.
func NewRemoteExecutor(rpc *RPCManager) *RemoteExecutor {
	return &RemoteExecutor{rpc: rpc}
}

// RemoteMatMul performs matrix multiplication on a remote worker.
func (re *RemoteExecutor) RemoteMatMul(ctx context.Context, target string, a, b *RPCTensor) (*RPCTensor, error) {
	result, err := re.rpc.client.Call(ctx, target, "matmul", a, b)
	if err != nil {
		return nil, err
	}
	return result.(*RPCTensor), nil
}

// RemoteAllReduce performs all-reduce using RPC.
func (re *RemoteExecutor) RemoteAllReduce(ctx context.Context, targets []string, t *RPCTensor) (*RPCTensor, error) {
	results := make([]*RPCTensor, len(targets))

	var wg sync.WaitGroup
	errs := make([]error, len(targets))

	for i, target := range targets {
		wg.Add(1)
		go func(idx int, tgt string) {
			defer wg.Done()
			result, err := re.rpc.client.Call(ctx, tgt, "allreduce", t)
			if err != nil {
				errs[idx] = err
				return
			}
			results[idx] = result.(*RPCTensor)
		}(i, target)
	}

	wg.Wait()

	for _, err := range errs {
		if err != nil {
			return nil, err
		}
	}

	// Sum all results (simplified all-reduce)
	return results[0], nil
}

// RemoteBroadcast broadcasts a tensor to remote workers.
func (re *RemoteExecutor) RemoteBroadcast(ctx context.Context, targets []string, t *RPCTensor) error {
	for _, target := range targets {
		_, err := re.rpc.client.Call(ctx, target, "broadcast", t)
		if err != nil {
			return err
		}
	}
	return nil
}

// RPCService provides standard RPC methods for distributed operations.
type RPCService struct {
	rpc *RPCManager
}

// NewRPCService creates an RPC service with standard methods.
func NewRPCService(rpc *RPCManager) *RPCService {
	svc := &RPCService{rpc: rpc}

	// Register standard methods
	rpc.RegisterMethod("matmul", svc.MatMul)
	rpc.RegisterMethod("allreduce", svc.AllReduce)
	rpc.RegisterMethod("broadcast", svc.Broadcast)
	rpc.RegisterMethod("ping", svc.Ping)
	rpc.RegisterMethod("get_rank", svc.GetRank)
	rpc.RegisterMethod("get_world_size", svc.GetWorldSize)

	return svc
}

// MatMul implements remote matrix multiplication.
func (svc *RPCService) MatMul(ctx context.Context, args ...interface{}) (interface{}, error) {
	if len(args) != 2 {
		return nil, ErrInvalidArgs
	}

	a, ok := args[0].(*RPCTensor)
	if !ok {
		return nil, ErrInvalidArgs
	}
	b, ok := args[1].(*RPCTensor)
	if !ok {
		return nil, ErrInvalidArgs
	}

	aT, err := a.ToTensor()
	if err != nil {
		return nil, err
	}
	bT, err := b.ToTensor()
	if err != nil {
		return nil, err
	}

	result, err := MatMulTensors(aT, bT)
	if err != nil {
		return nil, err
	}

	return NewRPCTensor(result), nil
}

// AllReduce implements remote all-reduce.
func (svc *RPCService) AllReduce(ctx context.Context, args ...interface{}) (interface{}, error) {
	if len(args) != 1 {
		return nil, ErrInvalidArgs
	}

	t, ok := args[0].(*RPCTensor)
	if !ok {
		return nil, ErrInvalidArgs
	}

	// Simplified: return as-is
	return t, nil
}

// Broadcast implements remote broadcast.
func (svc *RPCService) Broadcast(ctx context.Context, args ...interface{}) (interface{}, error) {
	if len(args) != 1 {
		return nil, ErrInvalidArgs
	}
	return args[0], nil
}

// Ping implements a ping method.
func (svc *RPCService) Ping(ctx context.Context, args ...interface{}) (interface{}, error) {
	return "pong", nil
}

// GetRank returns the current rank.
func (svc *RPCService) GetRank(ctx context.Context, args ...interface{}) (interface{}, error) {
	return svc.rpc.rank, nil
}

// GetWorldSize returns the world size.
func (svc *RPCService) GetWorldSize(ctx context.Context, args ...interface{}) (interface{}, error) {
	return svc.rpc.worldSize, nil
}

// MatMulTensors performs matrix multiplication on tensors.
func MatMulTensors(a, b *tensor.Tensor) (*tensor.Tensor, error) {
	// Simplified matrix multiplication
	// In production, would use tensor/math package
	m := a.Shape().Dim(0)
	k := a.Shape().Dim(1)
	n := b.Shape().Dim(1)

	if b.Shape().Dim(0) != k {
		return nil, errors.New("shape mismatch for matmul")
	}

	result, err := tensor.New(tensor.Float64, []int{m, n})
	if err != nil {
		return nil, err
	}

	aV := a.Float64()
	bV := b.Float64()
	rV := result.Float64()

	for i := 0; i < m; i++ {
		for j := 0; j < n; j++ {
			sum := 0.0
			for kk := 0; kk < k; kk++ {
				sum += aV[i*k+kk] * bV[kk*n+j]
			}
			rV[i*n+j] = sum
		}
	}

	return result, nil
}

// SerializeTensor serializes a tensor to JSON.
func SerializeTensor(t *tensor.Tensor) ([]byte, error) {
	rt := NewRPCTensor(t)
	return json.Marshal(rt)
}

// DeserializeTensor deserializes a tensor from JSON.
func DeserializeTensor(data []byte) (*tensor.Tensor, error) {
	var rt RPCTensor
	if err := json.Unmarshal(data, &rt); err != nil {
		return nil, err
	}
	return rt.ToTensor()
}
