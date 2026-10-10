// Package rpc provides a lightweight gRPC-style RPC framework with
// service definitions, message framing, and streaming.
package rpc

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"sync"
	"sync/atomic"
	"time"
)

// Common gRPC-style errors.
var (
	ErrServiceNotFound  = errors.New("service not found")
	ErrMethodNotFound   = errors.New("method not found")
	ErrInvalidFrame     = errors.New("invalid grpc frame")
	ErrDeadlineExceeded = errors.New("deadline exceeded")
	ErrStreamClosed     = errors.New("stream closed")
)

// ServiceDescriptor describes a gRPC service.
type ServiceDescriptor struct {
	Name    string
	Methods []MethodDescriptor
}

// MethodDescriptor describes one RPC method.
type MethodDescriptor struct {
	Name           string
	ClientStreaming bool
	ServerStreaming bool
}

// IsStreaming reports whether the method is streaming in either direction.
func (m MethodDescriptor) IsStreaming() bool {
	return m.ClientStreaming || m.ServerStreaming
}

// Message is a protobuf-style message with named fields.
type Message struct {
	Fields map[string]interface{}
}

// NewMessage creates an empty message.
func NewMessage() *Message {
	return &Message{Fields: make(map[string]interface{})}
}

// Set assigns a field value.
func (m *Message) Set(key string, value interface{}) *Message {
	if m.Fields == nil {
		m.Fields = make(map[string]interface{})
	}
	m.Fields[key] = value
	return m
}

// Get reads a field value.
func (m *Message) Get(key string) interface{} {
	return m.Fields[key]
}

// GetString reads a string field.
func (m *Message) GetString(key string) string {
	s, _ := m.Fields[key].(string)
	return s
}

// GetInt reads an int field.
func (m *Message) GetInt(key string) int {
	i, _ := m.Fields[key].(int)
	return i
}

// ServiceImpl handles unary and streaming requests.
type ServiceImpl interface {
	Unary(method string, req *Message) (*Message, error)
	ServerStream(method string, req *Message, send func(*Message) error) error
}

// Server hosts gRPC-style services.
type Server struct {
	mu       sync.RWMutex
	services map[string]ServiceDescriptor
	impls    map[string]ServiceImpl
	stats    ServerStats
	started  atomic.Bool
}

// ServerStats tracks server statistics.
type ServerStats struct {
	Requests    atomic.Int64
	Responses   atomic.Int64
	Errors      atomic.Int64
	StreamMsgs  atomic.Int64
}

// NewServer creates a gRPC-style server.
func NewServer() *Server {
	return &Server{
		services: make(map[string]ServiceDescriptor),
		impls:    make(map[string]ServiceImpl),
	}
}

// RegisterService registers a service and its implementation.
func (s *Server) RegisterService(desc ServiceDescriptor, impl ServiceImpl) error {
	if desc.Name == "" || impl == nil {
		return errors.New("invalid service registration")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.services[desc.Name]; ok {
		return fmt.Errorf("service %q already registered", desc.Name)
	}
	s.services[desc.Name] = desc
	s.impls[desc.Name] = impl
	return nil
}

// Start marks the server as serving.
func (s *Server) Start() error {
	if s.started.Swap(true) {
		return errors.New("server already started")
	}
	return nil
}

// Stop stops the server.
func (s *Server) Stop() error {
	s.started.Store(false)
	return nil
}

// Invoke handles a unary call: "Service.Method".
func (s *Server) Invoke(fullMethod string, req *Message) (*Message, error) {
	if !s.started.Load() {
		return nil, errors.New("server not started")
	}
	svc, method, err := splitMethod(fullMethod)
	if err != nil {
		return nil, err
	}
	s.mu.RLock()
	impl, ok := s.impls[svc]
	s.mu.RUnlock()
	if !ok {
		return nil, fmt.Errorf("%w: %s", ErrServiceNotFound, svc)
	}
	s.stats.Requests.Add(1)
	resp, err := impl.Unary(method, req)
	if err != nil {
		s.stats.Errors.Add(1)
		return nil, err
	}
	s.stats.Responses.Add(1)
	return resp, nil
}

// InvokeServerStream handles a server-streaming call.
func (s *Server) InvokeServerStream(fullMethod string, req *Message, send func(*Message) error) error {
	if !s.started.Load() {
		return errors.New("server not started")
	}
	svc, method, err := splitMethod(fullMethod)
	if err != nil {
		return err
	}
	s.mu.RLock()
	impl, ok := s.impls[svc]
	s.mu.RUnlock()
	if !ok {
		return fmt.Errorf("%w: %s", ErrServiceNotFound, svc)
	}
	s.stats.Requests.Add(1)
	if err := impl.ServerStream(method, req, func(m *Message) error {
		s.stats.StreamMsgs.Add(1)
		return send(m)
	}); err != nil {
		s.stats.Errors.Add(1)
		return err
	}
	s.stats.Responses.Add(1)
	return nil
}

// Services returns registered service names.
func (s *Server) Services() []string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	names := make([]string, 0, len(s.services))
	for n := range s.services {
		names = append(names, n)
	}
	return names
}

// Stats returns server statistics.
func (s *Server) Stats() *ServerStats { return &s.stats }

func splitMethod(full string) (string, string, error) {
	for i := 1; i < len(full); i++ {
		if full[i] == '.' {
			return full[:i], full[i+1:], nil
		}
	}
	return "", "", fmt.Errorf("%w: %q", ErrMethodNotFound, full)
}

// Client calls gRPC-style services.
type Client struct {
	conn    string
	server  *Server
	timeout time.Duration
	stats   ClientStats
	mu      sync.Mutex
}

// ClientStats tracks client statistics.
type ClientStats struct {
	Sent     atomic.Int64
	Received atomic.Int64
	Errors   atomic.Int64
}

// ClientOption configures a Client.
type ClientOption func(*Client)

// WithTimeout sets the default call timeout.
func WithTimeout(d time.Duration) ClientOption {
	return func(c *Client) { c.timeout = d }
}

// NewClient creates a client bound to a server (in-process transport).
func NewClient(conn string, server *Server, opts ...ClientOption) *Client {
	c := &Client{conn: conn, server: server, timeout: 5 * time.Second}
	for _, o := range opts {
		o(c)
	}
	return c
}

// Call performs a unary call.
func (c *Client) Call(fullMethod string, req *Message) (*Message, error) {
	c.mu.Lock()
	conn := c.conn
	c.mu.Unlock()
	_ = conn
	if c.server == nil {
		return nil, errors.New("client has no connection")
	}
	c.stats.Sent.Add(1)
	resp, err := c.server.Invoke(fullMethod, req)
	if err != nil {
		c.stats.Errors.Add(1)
		return nil, err
	}
	c.stats.Received.Add(1)
	return resp, nil
}

// Timeout returns the default call timeout.
func (c *Client) Timeout() time.Duration {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.timeout
}

// Stats returns client statistics.
func (c *Client) Stats() *ClientStats { return &c.stats }

// Conn returns the connection string.
func (c *Client) Conn() string { return c.conn }

// Frame is a length-prefixed message frame.
type Frame struct {
	Compressed bool
	Data       []byte
}

const frameHeaderSize = 5

// WriteFrame writes a length-prefixed frame.
func WriteFrame(w io.Writer, f Frame) error {
	hdr := make([]byte, frameHeaderSize)
	hdr[0] = 0
	if f.Compressed {
		hdr[0] = 1
	}
	binary.BigEndian.PutUint32(hdr[1:], uint32(len(f.Data)))
	if _, err := w.Write(hdr); err != nil {
		return err
	}
	if _, err := w.Write(f.Data); err != nil {
		return err
	}
	return nil
}

// ReadFrame reads a length-prefixed frame.
func ReadFrame(r io.Reader) (Frame, error) {
	hdr := make([]byte, frameHeaderSize)
	if _, err := io.ReadFull(r, hdr); err != nil {
		return Frame{}, err
	}
	f := Frame{Compressed: hdr[0] == 1}
	n := binary.BigEndian.Uint32(hdr[1:])
	f.Data = make([]byte, n)
	if _, err := io.ReadFull(r, f.Data); err != nil {
		return Frame{}, err
	}
	return f, nil
}

// ParamServerImplement is a parameter-server service.
type ParamServerImplement struct {
	mu    sync.RWMutex
	shard map[string][]float64
	stats ParamServerStats
}

// ParamServerStats tracks parameter-server statistics.
type ParamServerStats struct {
	Pushes atomic.Int64
	Pulls  atomic.Int64
}

// NewParamServerImplement creates a parameter-server implementation.
func NewParamServerImplement() *ParamServerImplement {
	return &ParamServerImplement{shard: make(map[string][]float64)}
}

// Unary handles Push/Pull methods.
func (p *ParamServerImplement) Unary(method string, req *Message) (*Message, error) {
	switch method {
	case "Push":
		key := req.GetString("key")
		var vals []float64
		if v, ok := req.Fields["values"]; ok {
			vals = toFloats(v)
		}
		p.mu.Lock()
		p.shard[key] = vals
		p.mu.Unlock()
		p.stats.Pushes.Add(1)
		return NewMessage().Set("ok", true).Set("n", len(vals)), nil
	case "Pull":
		key := req.GetString("key")
		p.mu.RLock()
		vals := p.shard[key]
		p.mu.RUnlock()
		p.stats.Pulls.Add(1)
		out := NewMessage()
		out.Fields["values"] = append([]float64(nil), vals...)
		return out.Set("ok", true).Set("n", len(vals)), nil
	default:
		return nil, fmt.Errorf("%w: ParamServer.%s", ErrMethodNotFound, method)
	}
}

// ServerStream is not used by the parameter server.
func (p *ParamServerImplement) ServerStream(method string, req *Message, send func(*Message) error) error {
	return fmt.Errorf("%w: ParamServer.%s", ErrMethodNotFound, method)
}

// Stats returns statistics.
func (p *ParamServerImplement) Stats() *ParamServerStats { return &p.stats }

// Keys returns the stored shard keys.
func (p *ParamServerImplement) Keys() []string {
	p.mu.RLock()
	defer p.mu.RUnlock()
	out := make([]string, 0, len(p.shard))
	for k := range p.shard {
		out = append(out, k)
	}
	return out
}

func toFloats(v interface{}) []float64 {
	if f, ok := v.([]float64); ok {
		return f
	}
	if f, ok := v.([]interface{}); ok {
		out := make([]float64, 0, len(f))
		for _, x := range f {
			switch n := x.(type) {
			case float64:
				out = append(out, n)
			case int:
				out = append(out, float64(n))
			}
		}
		return out
	}
	return nil
}