package tools

import (
	"fmt"
	"strings"
)

// Planning and decomposition, measured against ground truth.
//
// WS-D-008 asks for planning to be evaluated on multi-step tasks with ground
// truth, and for multi-agent coordination to be added only if a benchmark
// proves it beats a single agent. The second half is a constraint, not a
// suggestion, so the benchmark is built to *refuse* the coordination rather
// than to justify it.
//
// Ground truth here is deliberately mechanical: a task whose correct
// decomposition is known, so a planner is scored on whether it finds that
// decomposition rather than on whether its plan reads well. A plan that reads
// well and is wrong is worse than one that reads badly and is right, because
// only one of them can be checked.

// PlanStep is one step of a plan.
type PlanStep struct {
	// Description is what the step does.
	Description string `json:"description"`
	// Tool is the tool the step needs, when one is needed. Empty for a
	// thinking-only step.
	Tool string `json:"tool,omitempty"`
	// DependsOn lists the descriptions this step requires.
	DependsOn []string `json:"depends_on,omitempty"`
}

// Plan is a decomposition of a task.
type Plan struct {
	// Steps in the order they were produced.
	Steps []PlanStep `json:"steps"`
	// Explanation is the planner's rationale, so a wrong plan is diagnosable.
	Explanation string `json:"explanation,omitempty"`
}

// Validate checks a plan is well-formed: a dependency must reference a step
// that exists, and a step must not depend on itself.
func (p Plan) Validate() error {
	seen := map[string]bool{}
	for i, step := range p.Steps {
		if step.Description == "" {
			return fmt.Errorf("plan: step %d has no description", i)
		}
		if seen[step.Description] {
			return fmt.Errorf("plan: duplicate step %q", step.Description)
		}
		seen[step.Description] = true
	}
	for _, step := range p.Steps {
		for _, dep := range step.DependsOn {
			if dep == step.Description {
				return fmt.Errorf("plan: step %q depends on itself", step.Description)
			}
			if !seen[dep] {
				return fmt.Errorf("plan: step %q depends on unknown step %q", step.Description, dep)
			}
		}
	}
	// A dependency cycle makes the plan unexecutable, however well it reads.
	return p.checkAcyclic()
}

// checkAcyclic rejects a plan whose steps cannot be ordered.
func (p Plan) checkAcyclic() error {
	adjacency := map[string][]string{}
	for _, step := range p.Steps {
		adjacency[step.Description] = step.DependsOn
	}
	state := map[string]int{} // 0 unvisited, 1 visiting, 2 done
	var walk func(name string) error
	walk = func(name string) error {
		if state[name] == 1 {
			return fmt.Errorf("plan: dependency cycle through %q", name)
		}
		if state[name] == 2 {
			return nil
		}
		state[name] = 1
		for _, dep := range adjacency[name] {
			if _, ok := adjacency[dep]; !ok {
				continue
			}
			if err := walk(dep); err != nil {
				return err
			}
		}
		state[name] = 2
		return nil
	}
	for _, step := range p.Steps {
		if err := walk(step.Description); err != nil {
			return err
		}
	}
	return nil
}

// Order returns the steps in dependency order.
func (p Plan) Order() ([]PlanStep, error) {
	if err := p.Validate(); err != nil {
		return nil, err
	}
	byDescription := map[string]PlanStep{}
	for _, step := range p.Steps {
		byDescription[step.Description] = step
	}
	ordered := make([]PlanStep, 0, len(p.Steps))
	placed := map[string]bool{}
	for len(ordered) < len(p.Steps) {
		progressed := false
		for _, step := range p.Steps {
			if placed[step.Description] {
				continue
			}
			ready := true
			for _, dep := range step.DependsOn {
				if !placed[dep] {
					ready = false
					break
				}
			}
			if ready {
				ordered = append(ordered, step)
				placed[step.Description] = true
				progressed = true
			}
		}
		if !progressed {
			// Validate already ruled this out, so this is defensive.
			return nil, fmt.Errorf("plan: cannot order steps")
		}
	}
	return ordered, nil
}

// ---------------------------------------------------------------------------
// Ground truth and scoring
// ---------------------------------------------------------------------------

// Task is one planning benchmark case.
type Task struct {
	// ID names the case.
	ID string
	// Prompt is what the planner is given.
	Prompt string
	// GoldenSteps are the descriptions a correct plan contains.
	GoldenSteps []string
}

// Score is one plan's quality against a task.
type Score struct {
	// Recall is the fraction of golden steps the plan found.
	Recall float64 `json:"recall"`
	// Precision is the fraction of the plan's steps that are golden.
	Precision float64 `json:"precision"`
	// Ordered is true when the plan's golden steps appear in golden order.
	Ordered bool `json:"ordered"`
	// Valid is true when the plan is well-formed.
	Valid bool `json:"valid"`
}

// F1 is the harmonic mean, the single number a comparison needs.
func (s Score) F1() float64 {
	if s.Recall+s.Precision == 0 {
		return 0
	}
	return 2 * s.Recall * s.Precision / (s.Recall + s.Precision)
}

// ScorePlan grades a plan against a task.
func ScorePlan(plan Plan, task Task) Score {
	golden := map[string]bool{}
	for _, step := range task.GoldenSteps {
		golden[step] = true
	}

	produced := map[string]bool{}
	for _, step := range plan.Steps {
		produced[step.Description] = true
	}

	hits := 0
	for _, step := range task.GoldenSteps {
		if produced[step] {
			hits++
		}
	}

	score := Score{Valid: plan.Validate() == nil}
	if len(task.GoldenSteps) > 0 {
		score.Recall = float64(hits) / float64(len(task.GoldenSteps))
	}
	if len(plan.Steps) > 0 {
		correct := 0
		for _, step := range plan.Steps {
			if golden[step.Description] {
				correct++
			}
		}
		score.Precision = float64(correct) / float64(len(plan.Steps))
	}

	// The golden steps must also appear in order, because a plan that has the
	// right steps in the wrong order will not execute.
	inOrder := 0
	position := -1
	for _, step := range plan.Steps {
		if golden[step.Description] {
			if indexOf(task.GoldenSteps, step.Description) > position {
				inOrder++
				position = indexOf(task.GoldenSteps, step.Description)
			}
		}
	}
	score.Ordered = inOrder == len(task.GoldenSteps)
	return score
}

// indexOf is a helper for a small slice.
func indexOf(items []string, want string) int {
	for i, item := range items {
		if item == want {
			return i
		}
	}
	return -1
}

// Benchmark is a set of planning tasks.
type Benchmark struct {
	tasks []Task
}

// NewBenchmark builds a benchmark from tasks.
func NewBenchmark(tasks ...Task) *Benchmark {
	return &Benchmark{tasks: tasks}
}

// Add appends a task.
func (b *Benchmark) Add(task Task) {
	b.tasks = append(b.tasks, task)
}

// Tasks returns the benchmark's tasks.
func (b *Benchmark) Tasks() []Task {
	return append([]Task(nil), b.tasks...)
}

// Report is one planner's aggregate result.
type Report struct {
	Planner       string           `json:"planner"`
	Tasks         int              `json:"tasks"`
	MeanF1        float64          `json:"mean_f1"`
	MeanRecall    float64          `json:"mean_recall"`
	MeanPrecision float64          `json:"mean_precision"`
	Ordered       int              `json:"ordered"`
	Invalid       int              `json:"invalid"`
	Scores        map[string]Score `json:"scores"`
}

// Run scores a planner over the benchmark.
func (b *Benchmark) Run(name string, planner func(task Task) Plan) *Report {
	report := &Report{Planner: name, Scores: map[string]Score{}}
	var sumF1, sumRecall, sumPrecision float64

	for _, task := range b.tasks {
		plan := planner(task)
		score := ScorePlan(plan, task)
		report.Scores[task.ID] = score
		sumF1 += score.F1()
		sumRecall += score.Recall
		sumPrecision += score.Precision
		if score.Ordered {
			report.Ordered++
		}
		if !score.Valid {
			report.Invalid++
		}
	}

	if n := float64(len(b.tasks)); n > 0 {
		report.Tasks = len(b.tasks)
		report.MeanF1 = sumF1 / n
		report.MeanRecall = sumRecall / n
		report.MeanPrecision = sumPrecision / n
	}
	return report
}

// Compare reports whether a candidate beats a baseline.
//
// The comparison is strict on no axis: a candidate that gains recall by
// destroying precision, or that produces invalid plans, has not beaten
// anything. A comparison that averages across cases hides the case that
// regressed, so each is reported.
type Comparison struct {
	Baseline       string  `json:"baseline"`
	Candidate      string  `json:"candidate"`
	F1Delta        float64 `json:"f1_delta"`
	RecallDelta    float64 `json:"recall_delta"`
	PrecisionDelta float64 `json:"precision_delta"`
	Winner         string  `json:"winner"`
	Reason         string  `json:"reason"`
}

// Beats reports whether the candidate strictly improved.
func (c Comparison) Beats() bool { return c.Winner == "candidate" }

// ComparePlanners decides whether a candidate beats a baseline.
func ComparePlanners(baseline, candidate *Report) Comparison {
	comparison := Comparison{
		Baseline:       baseline.Planner,
		Candidate:      candidate.Planner,
		F1Delta:        candidate.MeanF1 - baseline.MeanF1,
		RecallDelta:    candidate.MeanRecall - baseline.MeanRecall,
		PrecisionDelta: candidate.MeanPrecision - baseline.MeanPrecision,
	}

	if candidate.Invalid > baseline.Invalid {
		comparison.Winner = "baseline"
		comparison.Reason = fmt.Sprintf("candidate produced invalid plans (%d vs %d)", candidate.Invalid, baseline.Invalid)
		return comparison
	}
	if candidate.MeanF1 <= baseline.MeanF1 {
		comparison.Winner = "baseline"
		comparison.Reason = fmt.Sprintf("no F1 gain (%.3f vs %.3f)", candidate.MeanF1, baseline.MeanF1)
		return comparison
	}
	if candidate.MeanPrecision < baseline.MeanPrecision {
		comparison.Winner = "baseline"
		comparison.Reason = "recall gained by losing precision"
	}
	if candidate.MeanRecall < baseline.MeanRecall {
		comparison.Winner = "baseline"
		comparison.Reason = "precision gained by losing recall"
	}
	if comparison.Winner == "" {
		comparison.Winner = "candidate"
		comparison.Reason = fmt.Sprintf("F1 improved %.3f to %.3f", baseline.MeanF1, candidate.MeanF1)
	}
	return comparison
}

// ---------------------------------------------------------------------------
// Sample tasks and planners
// ---------------------------------------------------------------------------

// SampleBenchmark is a small deterministic benchmark.
func SampleBenchmark() *Benchmark {
	return NewBenchmark(
		Task{
			ID:     "fix-login-bug",
			Prompt: "A user reports they cannot log in; find and fix the bug.",
			GoldenSteps: []string{
				"read the auth module",
				"reproduce the failure",
				"identify the root cause",
				"write a failing test",
				"apply the fix",
				"run the full suite",
			},
		},
		Task{
			ID:     "add-endpoint",
			Prompt: "Add an endpoint that returns the caller's profile.",
			GoldenSteps: []string{
				"read the router layout",
				"define the schema",
				"implement the handler",
				"add the route",
				"write tests",
			},
		},
		Task{
			ID:     "upgrade-dependency",
			Prompt: "Upgrade the HTTP client library and fix the fallout.",
			GoldenSteps: []string{
				"inspect current usage",
				"update the lockfile",
				"run the test suite",
				"fix breaking changes",
				"update the docs",
			},
		},
	)
}

// keywordPlanner decomposes a task from its own keywords. A deterministic
// planner, so the benchmark measures the scoring rather than a model.
func keywordPlanner(task Task) Plan {
	prompt := strings.ToLower(task.Prompt)
	var steps []string
	if strings.Contains(prompt, "fix") {
		steps = []string{"reproduce the failure", "identify the root cause", "apply the fix"}
	} else if strings.Contains(prompt, "add") || strings.Contains(prompt, "endpoint") {
		steps = []string{"define the schema", "implement the handler", "add the route"}
	} else {
		steps = []string{"inspect current usage", "update the lockfile"}
	}
	plan := Plan{}
	for _, step := range steps {
		plan.Steps = append(plan.Steps, PlanStep{Description: step})
	}
	return plan
}

// partialPlanner is a deliberately weaker planner, so the comparison has a
// baseline that does not win.
func partialPlanner(task Task) Plan {
	return Plan{Steps: []PlanStep{{Description: "look at the code"}}}
}
