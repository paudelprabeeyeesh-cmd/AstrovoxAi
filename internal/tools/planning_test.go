package tools

import (
	"strings"
	"testing"
)

// Planning is scored against ground truth, and the comparison is built to
// refuse the coordination rather than to justify it. A plan that reads well and
// is wrong is worse than one that reads badly and is right, because only one of
// them can be checked.
func planningTask() Task {
	return Task{
		ID:          "t",
		Prompt:      "fix it",
		GoldenSteps: []string{"a", "b", "c"},
	}
}

func TestPlanValidationRequiresDescriptions(t *testing.T) {
	if err := (Plan{Steps: []PlanStep{{Description: ""}}}).Validate(); err == nil {
		t.Fatal("a step with no description was accepted")
	}
}

func TestPlanValidationRejectsDuplicates(t *testing.T) {
	if err := (Plan{Steps: []PlanStep{{Description: "a"}, {Description: "a"}}}).Validate(); err == nil {
		t.Fatal("a duplicate step was accepted")
	}
}

func TestPlanValidationRejectsUnknownDependencies(t *testing.T) {
	if err := (Plan{Steps: []PlanStep{{Description: "a", DependsOn: []string{"ghost"}}}}).Validate(); err == nil {
		t.Fatal("a dependency on an unknown step was accepted")
	}
}

func TestPlanValidationRejectsSelfDependency(t *testing.T) {
	if err := (Plan{Steps: []PlanStep{{Description: "a", DependsOn: []string{"a"}}}}).Validate(); err == nil {
		t.Fatal("a self-dependency was accepted")
	}
}

func TestPlanValidationRejectsCycles(t *testing.T) {
	// A cycle makes the plan unexecutable, however well it reads.
	plan := Plan{Steps: []PlanStep{
		{Description: "a", DependsOn: []string{"b"}},
		{Description: "b", DependsOn: []string{"a"}},
	}}
	if err := plan.Validate(); err == nil {
		t.Fatal("a cyclic plan was accepted")
	}
}

func TestPlanOrderRespectsDependencies(t *testing.T) {
	plan := Plan{Steps: []PlanStep{
		{Description: "c", DependsOn: []string{"b"}},
		{Description: "b", DependsOn: []string{"a"}},
		{Description: "a"},
	}}
	ordered, err := plan.Order()
	if err != nil {
		t.Fatalf("order failed: %v", err)
	}
	if ordered[0].Description != "a" || ordered[1].Description != "b" || ordered[2].Description != "c" {
		t.Fatalf("order = %v", ordered)
	}
}

func TestScorePlanRecall(t *testing.T) {
	// Recall is the fraction of golden steps found.
	plan := Plan{Steps: []PlanStep{{Description: "a"}}}
	score := ScorePlan(plan, planningTask())
	if score.Recall < 0.33 || score.Recall > 0.34 {
		t.Fatalf("recall = %v, want about a third", score.Recall)
	}
}

func TestScorePlanPrecision(t *testing.T) {
	// Precision is the fraction of the plan that is golden, so a plan padded
	// with plausible-looking junk is penalised.
	plan := Plan{Steps: []PlanStep{
		{Description: "a"}, {Description: "noise"}, {Description: "more noise"},
	}}
	score := ScorePlan(plan, planningTask())
	if score.Precision > 0.34 {
		t.Fatalf("precision = %v, want a third; padding went unpunished", score.Precision)
	}
}

func TestScorePlanFlagsWrongOrder(t *testing.T) {
	// Right steps in the wrong order will not execute.
	plan := Plan{Steps: []PlanStep{
		{Description: "c"}, {Description: "b"}, {Description: "a"},
	}}
	if ScorePlan(plan, planningTask()).Ordered {
		t.Fatal("a reversed plan was scored as ordered")
	}
}

func TestScorePlanAcceptsRightOrder(t *testing.T) {
	plan := Plan{Steps: []PlanStep{
		{Description: "a"}, {Description: "b"}, {Description: "c"},
	}}
	if !ScorePlan(plan, planningTask()).Ordered {
		t.Fatal("a correctly ordered plan was not scored as ordered")
	}
}

func TestScorePlanMarksInvalidPlans(t *testing.T) {
	// An invalid plan scores zero rather than being graded on its content.
	plan := Plan{Steps: []PlanStep{{Description: "a", DependsOn: []string{"a"}}}}
	if ScorePlan(plan, planningTask()).Valid {
		t.Fatal("an invalid plan was marked valid")
	}
}

func TestPerfectPlanScoresOne(t *testing.T) {
	plan := Plan{Steps: []PlanStep{
		{Description: "a"}, {Description: "b"}, {Description: "c"},
	}}
	if score := ScorePlan(plan, planningTask()); score.F1() < 0.99 {
		t.Fatalf("F1 = %v, want 1.0 for a perfect plan", score.F1())
	}
}

func TestBenchmarkRunsOverEveryTask(t *testing.T) {
	benchmark := SampleBenchmark()
	report := benchmark.Run("keyword", keywordPlanner)
	if report.Tasks != len(benchmark.Tasks()) {
		t.Fatalf("report covers %d tasks, want %d", report.Tasks, len(benchmark.Tasks()))
	}
	if len(report.Scores) != len(benchmark.Tasks()) {
		t.Fatalf("scores = %d, want one per task", len(report.Scores))
	}
}

func TestComparisonRefusesAMereRelabel(t *testing.T) {
	// The same planner twice must not win: no F1 gain is not an improvement,
	// and a comparison that says otherwise is a comparison that always agrees.
	baseline := SampleBenchmark().Run("a", keywordPlanner)
	candidate := SampleBenchmark().Run("a", keywordPlanner)
	if ComparePlanners(baseline, candidate).Beats() {
		t.Fatal("an identical planner was reported as an improvement")
	}
}

func TestComparisonRefusesAnInvalidPlan(t *testing.T) {
	// A candidate that gains recall while producing invalid plans has not
	// beaten anything, because an invalid plan cannot execute at all.
	baseline := SampleBenchmark().Run("weak", partialPlanner)
	candidate := SampleBenchmark().Run("bigger", func(task Task) Plan {
		plan := keywordPlanner(task)
		plan.Steps = append(plan.Steps, PlanStep{Description: task.GoldenSteps[0], DependsOn: []string{task.GoldenSteps[0]}})
		return plan
	})
	comparison := ComparePlanners(baseline, candidate)
	if comparison.Winner == "candidate" && candidate.Invalid > 0 {
		t.Fatal("an invalid plan was counted as a gain")
	}
}

func TestComparisonRefusesGainByLosingPrecision(t *testing.T) {
	// Padding a plan with every possible step raises recall and destroys
	// precision; that is not an improvement.
	task := planningTask()
	padded := Plan{}
	for _, step := range task.GoldenSteps {
		padded.Steps = append(padded.Steps, PlanStep{Description: step})
	}
	for i := 0; i < 20; i++ {
		padded.Steps = append(padded.Steps, PlanStep{Description: "filler"})
	}
	score := ScorePlan(padded, task)
	if score.Recall < 0.99 {
		t.Fatalf("recall = %v", score.Recall)
	}
	if score.Precision > 0.2 {
		t.Fatalf("precision = %v; padding did not hurt", score.Precision)
	}
}

func TestComparisonSelectsTheBetterPlanner(t *testing.T) {
	baseline := SampleBenchmark().Run("weak", partialPlanner)
	candidate := SampleBenchmark().Run("keyword", keywordPlanner)
	if !ComparePlanners(baseline, candidate).Beats() {
		t.Fatal("the stronger planner did not beat the weaker one")
	}
}

func TestComparisonReasonIsReadable(t *testing.T) {
	baseline := SampleBenchmark().Run("weak", partialPlanner)
	candidate := SampleBenchmark().Run("keyword", keywordPlanner)
	reason := ComparePlanners(baseline, candidate).Reason
	if reason == "" {
		t.Fatal("a comparison carries no reason")
	}
	if !strings.Contains(reason, "F1") {
		t.Fatalf("the reason does not name the metric: %q", reason)
	}
}

func TestEmptyPlanScoresZero(t *testing.T) {
	if score := ScorePlan(Plan{}, planningTask()); score.F1() != 0 || score.Recall != 0 {
		t.Fatalf("an empty plan scored %v", score)
	}
}

func TestBenchmarkAddAppendsATask(t *testing.T) {
	benchmark := NewBenchmark()
	benchmark.Add(planningTask())
	if len(benchmark.Tasks()) != 1 {
		t.Fatal("Add did not append")
	}
}

func TestTasksIsACopy(t *testing.T) {
	// Mutating a returned task must not change the benchmark.
	benchmark := SampleBenchmark()
	seen := benchmark.Tasks()
	seen[0].Prompt = "mutated"
	if benchmark.Tasks()[0].Prompt == "mutated" {
		t.Fatal("the benchmark was mutated through a returned task")
	}
}
