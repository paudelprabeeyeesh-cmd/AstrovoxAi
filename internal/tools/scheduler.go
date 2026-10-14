package tools

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// Scheduled and background agents.
//
// A scheduled agent is the most dangerous thing in the system: it runs when
// nobody is watching, so a bug appears as a bill rather than as an error. Three
// rules follow from that.
//
//   1. A schedule carries its own budget, and the budget is the schedule's
//      rather than the run's. A schedule with no per-run ceiling runs the
//      interactive default, which was tuned for a human waiting for an answer.
//   2. A run that misses its deadline is stopped, not left to finish. A
//      background task that overruns delays the next one, and a chain of
//      overruns is a queue that never drains.
//   3. The result is notified, not silently discarded. A background agent whose
//      outcome nobody sees has no purpose.

// Notifier receives the outcome of a background run.
type Notifier interface {
	// Notify is called with the run's outcome. It must not block: a slow
	// notifier must not delay the queue.
	Notify(outcome Outcome)
}

// NotifyFunc adapts a function to Notifier.
type NotifyFunc func(outcome Outcome)

// Notify implements Notifier.
func (f NotifyFunc) Notify(outcome Outcome) { f(outcome) }

// Schedule describes when an agent runs.
type Schedule struct {
	// Name identifies the schedule.
	Name string
	// Task is the prompt given to the loop.
	Task string
	// Interval is how often to run. Zero means one-shot.
	Interval time.Duration
	// Limits bound one run.
	Limits Limits
	// Enabled gates the schedule without deleting it, so a paused schedule
	// survives a restart.
	Enabled bool
}

// Validate checks a schedule's configuration before it is accepted.
func (s Schedule) Validate() error {
	if s.Name == "" {
		return fmt.Errorf("tools: a schedule needs a name")
	}
	if s.Task == "" {
		return fmt.Errorf("tools: schedule %q needs a task", s.Name)
	}
	if s.Interval < 0 {
		return fmt.Errorf("tools: schedule %q has a negative interval", s.Name)
	}
	if s.Limits.MaxSteps <= 0 {
		return fmt.Errorf("tools: schedule %q has no step limit", s.Name)
	}
	if s.Limits.MaxDuration <= 0 {
		// A schedule with no duration ceiling can overrun into the next run.
		return fmt.Errorf("tools: schedule %q has no duration ceiling", s.Name)
	}
	return nil
}

// ScheduledRun is one recorded execution of a schedule.
type ScheduledRun struct {
	ScheduleName string    `json:"schedule_name"`
	RunID        string    `json:"run_id"`
	StartedAt    time.Time `json:"started_at"`
	EndedAt      time.Time `json:"ended_at"`
	StopReason   string    `json:"stop_reason"`
	Explanation  string    `json:"explanation,omitempty"`
	Steps        int       `json:"steps"`
	ToolCalls    int       `json:"tool_calls"`
	Cost         float64   `json:"cost"`
	// Overrun marks a run that exceeded its ceiling, which is the signal an
	// operator needs and the one a silent success hides.
	Overrun bool `json:"overrun,omitempty"`
}

// Scheduler runs loops on a schedule under per-run budgets.
type Scheduler struct {
	mu        sync.Mutex
	schedules map[string]*Schedule
	runs      []ScheduledRun
	factory   func(limits Limits) (*Registry, *Executor, ThinkFn, error)
	notifier  Notifier
	stop      chan struct{}
	wg        sync.WaitGroup
	started   bool
}

// NewScheduler returns a scheduler with a factory that builds one run.
//
// The factory is injected rather than the loop constructed internally, so a
// deployment decides how an agent is built and the scheduler stays testable
// without a provider.
func NewScheduler(factory func(limits Limits) (*Registry, *Executor, ThinkFn, error), notifier Notifier) *Scheduler {
	if notifier == nil {
		notifier = NotifyFunc(func(Outcome) {})
	}
	return &Scheduler{
		schedules: map[string]*Schedule{},
		factory:   factory,
		notifier:  notifier,
		stop:      make(chan struct{}),
	}
}

// Add registers a schedule. A schedule that does not validate is refused
// rather than accepted with defaults: a schedule that runs forever with no
// ceiling is the failure being designed against.
func (s *Scheduler) Add(schedule Schedule) error {
	if err := schedule.Validate(); err != nil {
		return err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.schedules[schedule.Name]; exists {
		return fmt.Errorf("tools: schedule %q already exists", schedule.Name)
	}
	copied := schedule
	s.schedules[schedule.Name] = &copied
	return nil
}

// Remove deletes a schedule.
func (s *Scheduler) Remove(name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.schedules[name]; !ok {
		return fmt.Errorf("tools: schedule %q not found", name)
	}
	delete(s.schedules, name)
	return nil
}

// SetEnabled pauses or resumes a schedule.
func (s *Scheduler) SetEnabled(name string, enabled bool) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	schedule, ok := s.schedules[name]
	if !ok {
		return fmt.Errorf("tools: schedule %q not found", name)
	}
	schedule.Enabled = enabled
	return nil
}

// Start begins running enabled schedules until Stop is called.
//
// One goroutine per schedule rather than a shared ticker, so a slow schedule
// cannot delay a fast one. A goroutine exits when the scheduler stops.
func (s *Scheduler) Start() error {
	s.mu.Lock()
	if s.started {
		s.mu.Unlock()
		return fmt.Errorf("tools: scheduler already started")
	}
	s.started = true
	schedules := make([]*Schedule, 0, len(s.schedules))
	for _, schedule := range s.schedules {
		schedules = append(schedules, schedule)
	}
	s.mu.Unlock()

	for _, schedule := range schedules {
		s.wg.Add(1)
		go func(schedule *Schedule) {
			defer s.wg.Done()
			s.runSchedule(schedule)
		}(schedule)
	}
	return nil
}

// Stop halts every schedule and waits for the running goroutines.
func (s *Scheduler) Stop() {
	s.mu.Lock()
	if s.started {
		s.started = false
		close(s.stop)
	}
	s.mu.Unlock()
	s.wg.Wait()
}

// runSchedule drives one schedule until the scheduler stops.
func (s *Scheduler) runSchedule(schedule *Schedule) {
	for {
		if schedule.Interval <= 0 {
			// One-shot: run once and stop.
			if schedule.Enabled {
				s.executeOnce(schedule)
			}
			return
		}

		if !schedule.Enabled {
			// Paused: wait a short period and re-check, so resuming does not
			// need a restart.
			select {
			case <-s.stop:
				return
			case <-time.After(schedule.Interval):
				continue
			}
		}

		s.executeOnce(schedule)

		select {
		case <-s.stop:
			return
		case <-time.After(schedule.Interval):
		}
	}
}

// executeOnce runs one iteration and records it.
func (s *Scheduler) executeOnce(schedule *Schedule) {
	registry, executor, think, err := s.factory(schedule.Limits)
	if err != nil {
		s.record(schedule, Outcome{StopReason: "factory_error", Explanation: err.Error()}, false)
		return
	}

	started := time.Now()
	loop := NewLoop(registry, executor, think, schedule.Limits)

	// A context bounds the run independently of the loop's own ceiling, so a
	// loop that ignores its limits is still stopped by the scheduler.
	ctx, cancel := context.WithTimeout(context.Background(), schedule.Limits.MaxDuration)
	defer cancel()

	outcome := loop.Run(ctx, schedule.Task)
	overrun := outcome.StopReason == StopDuration || time.Since(started) > schedule.Limits.MaxDuration
	s.record(schedule, outcome, overrun)
	s.notifier.Notify(outcome)
}

// record appends a run to the history.
func (s *Scheduler) record(schedule *Schedule, outcome Outcome, overrun bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.runs = append(s.runs, ScheduledRun{
		ScheduleName: schedule.Name,
		StartedAt:    time.Now(),
		StopReason:   outcome.StopReason,
		Explanation:  outcome.Explanation,
		Steps:        outcome.Steps,
		ToolCalls:    outcome.ToolCalls,
		Cost:         outcome.Cost,
		Overrun:      overrun,
	})
}

// Runs returns the recorded runs, newest first.
func (s *Scheduler) Runs() []ScheduledRun {
	s.mu.Lock()
	defer s.mu.Unlock()

	out := make([]ScheduledRun, len(s.runs))
	copy(out, s.runs)
	for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
		out[i], out[j] = out[j], out[i]
	}
	return out
}

// Schedules returns the registered schedules.
func (s *Scheduler) Schedules() []Schedule {
	s.mu.Lock()
	defer s.mu.Unlock()

	out := make([]Schedule, 0, len(s.schedules))
	for _, schedule := range s.schedules {
		out = append(out, *schedule)
	}
	return out
}

// Stats summarises scheduled execution.
func (s *Scheduler) Stats() map[string]int {
	s.mu.Lock()
	defer s.mu.Unlock()

	stats := map[string]int{"runs": len(s.runs), "overruns": 0, "schedules": len(s.schedules)}
	for _, run := range s.runs {
		if run.Overrun {
			stats["overruns"]++
		}
	}
	return stats
}
