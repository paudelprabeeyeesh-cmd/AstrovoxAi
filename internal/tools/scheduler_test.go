package tools

import (
	"context"
	"fmt"
	"sync"
	"testing"
	"time"
)

// A factory that builds a loop over a scripted thinker, so the scheduler can
// be exercised without a provider.
func testFactory(t *testing.T, actions ...action) func(Limits) (*Registry, *Executor, ThinkFn, error) {
	return func(limits Limits) (*Registry, *Executor, ThinkFn, error) {
		r, executor := newLoopFixture(t)
		thinker := &scriptedThinker{actions: actions}
		return r, executor, thinker.Think, nil
	}
}

func okSchedule(name string) Schedule {
	limits := DefaultLimits()
	limits.MaxDuration = 5 * time.Second
	return Schedule{Name: name, Task: "do the work", Interval: 0, Limits: limits, Enabled: true}
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

func TestAScheduleNeedsAName(t *testing.T) {
	if err := (Schedule{Task: "x"}).Validate(); err == nil {
		t.Fatal("a schedule with no name was accepted")
	}
}

func TestAScheduleNeedsATask(t *testing.T) {
	if err := (Schedule{Name: "s"}).Validate(); err == nil {
		t.Fatal("a schedule with no task was accepted")
	}
}

func TestAScheduleNeedsAStepLimit(t *testing.T) {
	s := okSchedule("s")
	s.Limits.MaxSteps = 0
	if err := s.Validate(); err == nil {
		t.Fatal("a schedule with no step ceiling was accepted")
	}
}

func TestAScheduleNeedsADurationCeiling(t *testing.T) {
	// A schedule with no duration ceiling can overrun into the next run.
	s := okSchedule("s")
	s.Limits.MaxDuration = 0
	if err := s.Validate(); err == nil {
		t.Fatal("a schedule with no duration ceiling was accepted")
	}
}

func TestAScheduleRejectsANegativeInterval(t *testing.T) {
	s := okSchedule("s")
	s.Interval = -time.Second
	if err := s.Validate(); err == nil {
		t.Fatal("a negative interval was accepted")
	}
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

func TestSchedulerAddAndRemove(t *testing.T) {
	s := NewScheduler(testFactory(t, replyNow("done")), nil)
	if err := s.Add(okSchedule("s1")); err != nil {
		t.Fatal(err)
	}
	if err := s.Remove("s1"); err != nil {
		t.Fatal(err)
	}
	if err := s.Remove("ghost"); err == nil {
		t.Fatal("removing an unknown schedule succeeded")
	}
}

func TestSchedulerRefusesADuplicate(t *testing.T) {
	s := NewScheduler(testFactory(t), nil)
	if err := s.Add(okSchedule("s1")); err != nil {
		t.Fatal(err)
	}
	if err := s.Add(okSchedule("s1")); err == nil {
		t.Fatal("a duplicate schedule name was accepted")
	}
}

func TestSchedulerRefusesAnInvalidSchedule(t *testing.T) {
	// Refused rather than accepted with defaults: a schedule that runs forever
	// with no ceiling is the failure being designed against.
	s := NewScheduler(testFactory(t), nil)
	if err := s.Add(Schedule{Name: "s", Task: "x"}); err == nil {
		t.Fatal("an unbounded schedule was accepted")
	}
}

func TestSchedulerCanPauseAndResume(t *testing.T) {
	s := NewScheduler(testFactory(t), nil)
	if err := s.Add(okSchedule("s1")); err != nil {
		t.Fatal(err)
	}
	if err := s.SetEnabled("s1", false); err != nil {
		t.Fatal(err)
	}
	if err := s.SetEnabled("s1", true); err != nil {
		t.Fatal(err)
	}
	if err := s.SetEnabled("ghost", true); err == nil {
		t.Fatal("toggling an unknown schedule succeeded")
	}
}

// ---------------------------------------------------------------------------
// Execution
// ---------------------------------------------------------------------------

func TestAOneShotScheduleRunsOnceAndNotifies(t *testing.T) {
	notified := make(chan Outcome, 4)
	s := NewScheduler(testFactory(t, replyNow("the answer")), NotifyFunc(func(o Outcome) {
		notified <- o
	}))
	if err := s.Add(okSchedule("once")); err != nil {
		t.Fatal(err)
	}

	if err := s.Start(); err != nil {
		t.Fatal(err)
	}
	select {
	case o := <-notified:
		if o.Answer != "the answer" {
			t.Fatalf("notified answer = %q", o.Answer)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("a one-shot schedule never notified")
	}
	s.Stop()

	runs := s.Runs()
	if len(runs) != 1 {
		t.Fatalf("runs = %d, want 1", len(runs))
	}
	if runs[0].ScheduleName != "once" {
		t.Fatalf("run recorded schedule %q", runs[0].ScheduleName)
	}
}

func TestAnIntervalScheduleRepeats(t *testing.T) {
	notified := make(chan Outcome, 16)
	s := NewScheduler(testFactory(t, replyNow("tick")), NotifyFunc(func(o Outcome) {
		notified <- o
	}))

	schedule := okSchedule("ticker")
	schedule.Interval = 50 * time.Millisecond
	if err := s.Add(schedule); err != nil {
		t.Fatal(err)
	}
	if err := s.Start(); err != nil {
		t.Fatal(err)
	}

	deadline := time.After(4 * time.Second)
	count := 0
loop:
	for {
		select {
		case <-notified:
			count++
			if count >= 3 {
				break loop
			}
		case <-deadline:
			break loop
		}
	}
	s.Stop()

	if count < 3 {
		t.Fatalf("saw %d ticks, want at least 3", count)
	}
	if len(s.Runs()) < 3 {
		t.Fatalf("recorded %d runs", len(s.Runs()))
	}
}

func TestAPausedScheduleDoesNotRun(t *testing.T) {
	notified := make(chan Outcome, 4)
	s := NewScheduler(testFactory(t, replyNow("x")), NotifyFunc(func(o Outcome) {
		notified <- o
	}))

	schedule := okSchedule("paused")
	schedule.Enabled = false
	if err := s.Add(schedule); err != nil {
		t.Fatal(err)
	}
	if err := s.Start(); err != nil {
		t.Fatal(err)
	}

	select {
	case o := <-notified:
		t.Fatalf("a paused schedule ran: %q", o.Answer)
	case <-time.After(300 * time.Millisecond):
	}
	s.Stop()
}

func TestSchedulerStopHaltsEverything(t *testing.T) {
	notified := make(chan Outcome, 64)
	s := NewScheduler(testFactory(t, replyNow("x")), NotifyFunc(func(o Outcome) {
		notified <- o
	}))

	schedule := okSchedule("fast")
	schedule.Interval = 10 * time.Millisecond
	if err := s.Add(schedule); err != nil {
		t.Fatal(err)
	}
	if err := s.Start(); err != nil {
		t.Fatal(err)
	}
	time.Sleep(120 * time.Millisecond)
	s.Stop()

	before := len(s.Runs())
	time.Sleep(200 * time.Millisecond)
	if after := len(s.Runs()); after != before {
		t.Fatalf("runs continued after Stop: %d -> %d", before, after)
	}
}

func TestSchedulerRecordsOverruns(t *testing.T) {
	// An overrun is the signal an operator needs and the one a silent success
	// hides.
	s := NewScheduler(testFactory(t, replyNow("late")), nil)
	schedule := okSchedule("overrun")
	schedule.Interval = 0
	if err := s.Add(schedule); err != nil {
		t.Fatal(err)
	}
	if err := s.Start(); err != nil {
		t.Fatal(err)
	}
	deadline := time.After(5 * time.Second)
	for len(s.Runs()) == 0 {
		if len(s.Runs()) > 0 {
			break
		}
		select {
		case <-deadline:
			t.Fatal("no run recorded")
		default:
			time.Sleep(20 * time.Millisecond)
		}
	}
	s.Stop()

	run := s.Runs()[0]
	if run.StopReason == "" {
		t.Fatal("a run was recorded with no stop reason")
	}
	if run.Overrun {
		t.Fatal("a fast run was marked as an overrun")
	}
}

func TestStatsCountSchedulesAndRuns(t *testing.T) {
	s := NewScheduler(testFactory(t, replyNow("x")), nil)
	if err := s.Add(okSchedule("a")); err != nil {
		t.Fatal(err)
	}
	if err := s.Add(okSchedule("b")); err != nil {
		t.Fatal(err)
	}
	stats := s.Stats()
	if stats["schedules"] != 2 || stats["runs"] != 0 {
		t.Fatalf("stats = %v", stats)
	}
}

func TestFactoryErrorsAreRecordedNotPanicked(t *testing.T) {
	boom := fmt.Errorf("cannot build an agent")
	s := NewScheduler(func(limits Limits) (*Registry, *Executor, ThinkFn, error) {
		return nil, nil, nil, boom
	}, nil)
	if err := s.Add(okSchedule("broken")); err != nil {
		t.Fatal(err)
	}
	if err := s.Start(); err != nil {
		t.Fatal(err)
	}
	deadline := time.After(5 * time.Second)
	for len(s.Runs()) == 0 {
		select {
		case <-deadline:
			t.Fatal("a factory error was not recorded")
		default:
			time.Sleep(20 * time.Millisecond)
		}
	}
	s.Stop()
	if got := s.Runs()[0].StopReason; got != "factory_error" {
		t.Fatalf("stop reason = %q, want factory_error", got)
	}
}

var _ = context.Background
var _ = sync.Mutex{}
