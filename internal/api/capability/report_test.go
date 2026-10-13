package capability

import (
	"strings"
	"testing"
)

func TestRateCountsOnlyCasesThatRan(t *testing.T) {
	// A skipped case must not dilute the pass rate: it did not run, so it
	// is neither evidence for nor against.
	g := Grade{Name: "x", Passed: 3, Failed: 0, Skipped: 7}
	if g.Rate() != 1.0 {
		t.Fatalf("Rate = %v, want 1.0", g.Rate())
	}
}

func TestRateIsZeroWhenNothingRan(t *testing.T) {
	// An empty suite is not a passing suite.
	g := Grade{Name: "x"}
	if g.Rate() != 0 {
		t.Fatalf("Rate = %v, want 0", g.Rate())
	}
	if g.AllPassed() {
		t.Fatal("an empty suite reported all-passed")
	}
}

func TestAllPassedRequiresAtLeastOneCase(t *testing.T) {
	// Zero cases and zero failures is not a green suite.
	g := Grade{Name: "x", Passed: 0, Failed: 0}
	if g.AllPassed() {
		t.Fatal("an empty suite reported all-passed")
	}
}

func TestRateReflectsFailures(t *testing.T) {
	g := Grade{Name: "x", Passed: 3, Failed: 1}
	if g.Rate() != 0.75 {
		t.Fatalf("Rate = %v, want 0.75", g.Rate())
	}
	if g.AllPassed() {
		t.Fatal("a suite with a failure reported all-passed")
	}
}

func TestReportRateIsCaseWeighted(t *testing.T) {
	// A three-case suite must not outvote a four-hundred-case suite.
	r := &Report{}
	r.Add(Grade{Name: "small", Passed: 3, Failed: 0})
	r.Add(Grade{Name: "large", Passed: 300, Failed: 100})
	want := 303.0 / 403.0
	got := r.Rate()
	if got < want-0.001 || got > want+0.001 {
		t.Fatalf("Rate = %v, want %v", got, want)
	}
}

func TestReportTotalsAggregate(t *testing.T) {
	r := &Report{}
	r.Add(Grade{Name: "a", Passed: 2, Failed: 1, Skipped: 3})
	r.Add(Grade{Name: "b", Passed: 4, Failed: 0, Skipped: 5})
	p, f, s := r.Totals()
	if p != 6 || f != 1 || s != 8 {
		t.Fatalf("totals = %d/%d/%d, want 6/1/8", p, f, s)
	}
}

func TestReportCompleteRequiresEverySuiteGreen(t *testing.T) {
	r := &Report{}
	r.Add(Grade{Name: "a", Passed: 2, Failed: 0})
	if !r.Complete() {
		t.Fatal("a green suite was incomplete")
	}
	r.Add(Grade{Name: "b", Passed: 2, Failed: 1})
	if r.Complete() {
		t.Fatal("a report with a failing suite reported complete")
	}
}

func TestReportCompleteRequiresASuite(t *testing.T) {
	r := &Report{}
	if r.Complete() {
		t.Fatal("an empty report reported complete")
	}
}

func TestRenderListsEverySuiteAndItsScope(t *testing.T) {
	r := &Report{}
	r.Add(Grade{Name: "zzz.last", Passed: 1, Failed: 0, Scope: "alpha"})
	r.Add(Grade{Name: "aaa.first", Passed: 1, Failed: 0, Scope: "beta"})
	out := r.String()

	for _, want := range []string{"aaa.first", "beta", "zzz.last", "alpha"} {
		if !strings.Contains(out, want) {
			t.Fatalf("render missing %q:\n%s", want, out)
		}
	}
}

func TestRenderReportsStatusHonely(t *testing.T) {
	r := &Report{}
	r.Add(Grade{Name: "a", Passed: 1, Failed: 0})
	if !strings.Contains(r.String(), "all measured suites green") {
		t.Fatal("a green report did not say so")
	}
	r.Add(Grade{Name: "b", Passed: 0, Failed: 1})
	if !strings.Contains(r.String(), "NOT all suites green") {
		t.Fatal("a failing report claimed to be green")
	}
}

func TestRenderMarksHeldOut(t *testing.T) {
	r := &Report{}
	r.Add(Grade{Name: "held", Passed: 1, Failed: 0, HeldOut: true})
	if !strings.Contains(r.String(), "held-out") {
		t.Fatal("a held-out suite was not marked")
	}
}

func TestRenderPublishesNoSingleScore(t *testing.T) {
	// The whole point of the package: an aggregate would hide which
	// surfaces are covered.
	r := &Report{}
	r.Add(Grade{Name: "a", Passed: 5, Failed: 5})
	if strings.Contains(r.String(), "score") &&
		!strings.Contains(r.String(), "no single score") {
		t.Fatal("render published an aggregate score")
	}
}

func TestStringMatchesRender(t *testing.T) {
	r := &Report{}
	r.Add(Grade{Name: "a", Passed: 1, Failed: 0})
	var b strings.Builder
	r.Render(&b)
	if r.String() != b.String() {
		t.Fatal("String and Render disagree")
	}
}
