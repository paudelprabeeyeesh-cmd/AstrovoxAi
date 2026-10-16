// Package controlplane provides the distributed execution control plane.
//
// This file implements the TCP server that hosts the Coordinator. Worker
// processes connect to this server over TCP to register, send heartbeats,
// and report task results. Clients connect to submit tasks.
//
// The server uses JSON-encoded messages over TCP. Each connection is
// handled in its own goroutine; the Coordinator's mutex serializes
// access to shared state.
package controlplane

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"sync"
)

// Server is the TCP server that hosts the Coordinator.
type Server struct {
	addr     string
	listener net.Listener
	coord    *Coordinator
	mu       sync.Mutex
	// conns maps worker ID to connection.
	conns map[string]net.Conn
	// connToWorker maps connection to worker ID.
	connToWorker map[net.Conn]string
	closed       bool
}

// NewServer creates a coordinator server listening on addr.
func NewServer(addr string, coord *Coordinator) *Server {
	s := &Server{
		addr:     addr,
		coord:    coord,
		conns:    make(map[string]net.Conn),
		connToWorker: make(map[net.Conn]string),
	}
	coord.SetServer(s)
	return s
}

// ListenAndServe starts listening for connections and blocks until ctx is
// cancelled or the server is shut down.
func (s *Server) ListenAndServe(ctx context.Context) error {
	ln, err := net.Listen("tcp", s.addr)
	if err != nil {
		return fmt.Errorf("listen: %w", err)
	}
	s.listener = ln

	// Accept loop.
	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				select {
				case <-ctx.Done():
					return
				default:
					continue
				}
			}
			s.mu.Lock()
			if s.closed {
				conn.Close()
				s.mu.Unlock()
				return
			}
			s.mu.Unlock()
			go s.handleConn(conn)
		}
	}()

	<-ctx.Done()
	s.mu.Lock()
	s.closed = true
	s.mu.Unlock()
	return s.listener.Close()
}

// handleConn handles a single connection. It reads JSON messages and
// dispatches them based on their type.
func (s *Server) handleConn(conn net.Conn) {
	defer func() {
		s.mu.Lock()
		if workerID, ok := s.connToWorker[conn]; ok {
			delete(s.conns, workerID)
			delete(s.connToWorker, conn)
		}
		s.mu.Unlock()
		conn.Close()
	}()

	dec := json.NewDecoder(conn)

	for {
		var envelope struct {
			Type string          `json:"type"`
			Data   json.RawMessage `json:"data"`
		}

		if err := dec.Decode(&envelope); err != nil {
			if err == io.EOF {
				return
			}
			return
		}

		switch envelope.Type {
		case "worker_registration":
			var reg WorkerRegistration
			if err := json.Unmarshal(envelope.Data, &reg); err != nil {
				s.sendError(conn, err)
				continue
			}
			if err := s.coord.RegisterWorker(reg); err != nil {
				s.sendError(conn, err)
				continue
			}
			// Store the connection keyed by worker ID.
			s.mu.Lock()
			s.conns[reg.WorkerID] = conn
			s.connToWorker[conn] = reg.WorkerID
			s.mu.Unlock()
			s.sendJSON(conn, &WorkerResult{
				ProtocolVersion: ProtocolVersion,
				TaskID:          "registration",
				State:           TaskSucceeded,
			})

		case "worker_heartbeat":
			var hb WorkerHeartbeat
			if err := json.Unmarshal(envelope.Data, &hb); err != nil {
				s.sendError(conn, err)
				continue
			}
			if err := s.coord.WorkerHeartbeat(hb); err != nil {
				s.sendError(conn, err)
				continue
			}
			s.sendJSON(conn, &WorkerResult{
				ProtocolVersion: ProtocolVersion,
				TaskID:          "heartbeat",
				State:           TaskSucceeded,
			})

		case "worker_result":
			var res WorkerResult
			if err := json.Unmarshal(envelope.Data, &res); err != nil {
				s.sendError(conn, err)
				continue
			}
			if err := s.coord.WorkerResult(res); err != nil {
				s.sendError(conn, err)
				continue
			}
			s.sendJSON(conn, &WorkerResult{
				ProtocolVersion: ProtocolVersion,
				TaskID:          res.TaskID,
				State:           TaskSucceeded,
			})

		case "submit_task":
			var req TaskRequest
			if err := json.Unmarshal(envelope.Data, &req); err != nil {
				s.sendError(conn, err)
				continue
			}
			resp, err := s.coord.SubmitTask(context.Background(), req)
			if err != nil {
				s.sendError(conn, err)
				continue
			}
			s.sendJSON(conn, resp)

		case "get_task_status":
			var req struct {
				TaskID string `json:"task_id"`
			}
			if err := json.Unmarshal(envelope.Data, &req); err != nil {
				s.sendError(conn, err)
				continue
			}
			resp, err := s.coord.GetTaskStatus(req.TaskID)
			if err != nil {
				s.sendError(conn, err)
				continue
			}
			s.sendJSON(conn, resp)

		default:
			s.sendError(conn, errors.New("unknown message type: "+envelope.Type))
		}
	}
}

// SendToWorker sends a message to a specific worker by ID.
func (s *Server) SendToWorker(workerID string, msg interface{}) error {
	s.mu.Lock()
	conn, ok := s.conns[workerID]
	s.mu.Unlock()
	if !ok {
		return errors.New("worker not connected: " + workerID)
	}
	return s.sendJSON(conn, msg)
}

// Close closes the server and all connections.
func (s *Server) Close() error {
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return nil
	}
	s.closed = true
	conns := make([]net.Conn, 0, len(s.conns))
	for _, c := range s.conns {
		conns = append(conns, c)
	}
	s.mu.Unlock()

	for _, c := range conns {
		c.Close()
	}
	if s.listener != nil {
		return s.listener.Close()
	}
	return nil
}

// sendJSON marshals v to JSON and writes it to conn.
func (s *Server) sendJSON(conn net.Conn, v interface{}) error {
	data, err := json.Marshal(v)
	if err != nil {
		return err
	}
	_, err = conn.Write(append(data, '\n'))
	return err
}

// sendError writes an error response to conn.
func (s *Server) sendError(conn net.Conn, err error) {
	resp := &WorkerResult{
		ProtocolVersion: ProtocolVersion,
		TaskID:          "error",
		State:           TaskFailed,
		Error:           err.Error(),
	}
	s.sendJSON(conn, resp)
}