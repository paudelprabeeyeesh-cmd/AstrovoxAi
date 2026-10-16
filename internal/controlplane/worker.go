// Package controlplane implements the distributed execution control plane.
//
// Worker is a separate OS process that connects to the coordinator,
// registers its capabilities, receives tasks, executes them, and reports
// results. It runs independently of the coordinator and can be started,
// stopped, and scaled independently.
//
// The worker communicates with the coordinator over TCP using JSON-encoded
// protocol messages defined in protocol.go.
package controlplane

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"sync"
	"sync/atomic"
	"time"
)

// Worker executes tasks assigned by the coordinator.
type Worker struct {
	id       string
	cap      []string
	res      ResourceRequirements
	coordinatorAddr string
	mu       sync.Mutex
	conn     net.Conn
	decoder  *json.Decoder
	encoder  *json.Encoder
	tasks    map[string]*TaskSpec  // taskID -> spec for active tasks
	running  atomic.Bool
	stopCh   chan struct{}
}

// NewWorker creates a worker with the given ID, capabilities, and
// resources. The coordinator address is the host:port of the coordinator's
// TCP server.
func NewWorker(id string, caps []string, res ResourceRequirements, coordinatorAddr string) *Worker {
	return &Worker{
		id:               id,
		cap:              caps,
		res:              res,
		coordinatorAddr:  coordinatorAddr,
		tasks:            make(map[string]*TaskSpec),
		stopCh:           make(chan struct{}),
	}
}

// Run connects to the coordinator, registers, and processes tasks until
// ctx is cancelled or the connection is lost.
func (w *Worker) Run(ctx context.Context) error {
	conn, err := net.DialTimeout("tcp", w.coordinatorAddr, 10*time.Second)
	if err != nil {
		return fmt.Errorf("connect to coordinator: %w", err)
	}
	defer conn.Close()

	w.mu.Lock()
	w.conn = conn
	w.decoder = json.NewDecoder(conn)
	w.encoder = json.NewEncoder(conn)
	w.mu.Unlock()

	// Register with the coordinator.
	if err := w.register(ctx); err != nil {
		return fmt.Errorf("register: %w", err)
	}

	// Start heartbeat goroutine.
	hbCtx, hbCancel := context.WithCancel(ctx)
	defer hbCancel()
	go w.heartbeatLoop(hbCtx)

	// Main loop: read task assignments from coordinator.
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		// Read next message from coordinator.
		var msg json.RawMessage
		if err := w.decoder.Decode(&msg); err != nil {
			if err == io.EOF {
				return errors.New("coordinator connection closed")
			}
			return fmt.Errorf("read message: %w", err)
		}

		// Determine message type.
		var envelope struct {
			Type string `json:"type"`
		}
		if err := json.Unmarshal(msg, &envelope); err != nil {
			return fmt.Errorf("parse message type: %w", err)
		}

		switch envelope.Type {
		case "task_assignment":
			var assign WorkerAssignment
			if err := json.Unmarshal(msg, &assign); err != nil {
				return fmt.Errorf("parse task assignment: %w", err)
			}
			if err := w.handleTaskAssignment(ctx, &assign); err != nil {
				return fmt.Errorf("handle task assignment: %w", err)
			}

		case "shutdown":
			return nil

		default:
			// Unknown message type; ignore.
		}
	}
}

// register sends a WorkerRegistration to the coordinator.
func (w *Worker) register(ctx context.Context) error {
	reg := WorkerRegistration{
		ProtocolVersion: ProtocolVersion,
		WorkerID:        w.id,
		Capabilities:    w.cap,
		Resources:       w.res,
		TenantQuotas:    map[string]int64{},
	}
	return w.send(reg, "worker_registration")
}

// heartbeatLoop sends periodic heartbeats to the coordinator.
func (w *Worker) heartbeatLoop(ctx context.Context) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			hb := WorkerHeartbeat{
				ProtocolVersion: ProtocolVersion,
				WorkerID:        w.id,
				Timestamp:       time.Now(),
				ActiveTasks:     w.activeTaskCount(),
				CompletedTasks:  0,
				FailedTasks:     0,
			}
			if err := w.send(hb, "worker_heartbeat"); err != nil {
				return
			}
		}
	}
}

// handleTaskAssignment processes a task assignment from the coordinator.
func (w *Worker) handleTaskAssignment(ctx context.Context, assign *WorkerAssignment) error {
	w.mu.Lock()
	w.tasks[assign.TaskID] = &assign.Spec
	w.mu.Unlock()

	// Execute the task in a separate goroutine so we can respond to
	// cancellation.
	go func() {
		ctx, cancel := context.WithDeadline(ctx, assign.Deadline)
		defer cancel()

		result, err := w.executeTask(ctx, assign.Spec)

		res := WorkerResult{
			ProtocolVersion: ProtocolVersion,
			TaskID:          assign.TaskID,
			Attempt:         assign.Attempt,
		}

		if err != nil {
			res.State = TaskFailed
			res.Error = err.Error()
		} else {
			res.State = TaskSucceeded
			res.Output = result
		}

		if err := w.send(res, "worker_result"); err != nil {
			// If we can't send the result, there's not much we can do.
			// The coordinator will timeout and reassign.
			return
		}

		w.mu.Lock()
		delete(w.tasks, assign.TaskID)
		w.mu.Unlock()
	}()

	return nil
}

// executeTask runs the task's operation. This is where the actual
// computation happens. For now, it supports a small set of built-in
// operations; external models and graphs are executed by delegating
// to the model/inference engine (not yet integrated).
func (w *Worker) executeTask(ctx context.Context, spec TaskSpec) ([]byte, error) {
	switch spec.Operation {
	case "ping":
		return []byte("pong"), nil
	case "echo":
		return spec.Payload, nil
	default:
		return nil, fmt.Errorf("unsupported operation: %s", spec.Operation)
	}
}

// activeTaskCount returns the number of tasks currently executing.
func (w *Worker) activeTaskCount() int {
	w.mu.Lock()
	defer w.mu.Unlock()
	return len(w.tasks)
}

// send marshals and sends a message to the coordinator.
func (w *Worker) send(msg interface{}, msgType string) error {
	w.mu.Lock()
	defer w.mu.Unlock()

	if w.conn == nil {
		return errors.New("not connected")
	}

	// Wrap with type for demultiplexing on the coordinator side.
	envelope := struct {
		Type string      `json:"type"`
		Data interface{} `json:"data"`
	}{
		Type: msgType,
		Data: msg,
	}

	return w.encoder.Encode(envelope)
}

// Shutdown gracefully shuts down the worker.
func (w *Worker) Shutdown(ctx context.Context) error {
	w.running.Store(false)
	close(w.stopCh)
	if w.conn != nil {
		return w.conn.Close()
	}
	return nil
}