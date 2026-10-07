package scheduler

import "sync"

// Event is a scheduler event notification.
type Event struct {
	Type string
	Task *Task
	Time int64
}

// EventBus dispatches events to subscribed handlers.
type EventBus struct {
	mu       sync.RWMutex
	handlers map[string][]func(Event)
}

// NewEventBus creates an empty event bus.
func NewEventBus() *EventBus {
	return &EventBus{handlers: make(map[string][]func(Event))}
}

// Subscribe registers a handler for an event type.
func (b *EventBus) Subscribe(topic string, handler func(Event)) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.handlers[topic] = append(b.handlers[topic], handler)
}

// Publish delivers an event to all handlers of its type.
func (b *EventBus) Publish(e Event) {
	b.mu.RLock()
	handlers := b.handlers[e.Type]
	b.mu.RUnlock()
	for _, h := range handlers {
		h(e)
	}
}
