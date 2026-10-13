// Package capability defines an honest, reproducible capability assessment.
//
// There is no accepted AGI benchmark. Any repository that prints "AGI
// Score: 98%" with no methodology is making the exact overclaiming the
// engineering register warns about. This package deliberately does not
// produce a single number: it reports measured pass rates per suite, with
// the suite's own scope stated, so a reader can see what was and was not
// tested.
//
// Each suite is a set of cases with a deterministic grader. The graders do
// not need a model: they score the properties an implementation must have
// (does the guard refuse before the connection, is the token single-use,
// is the write owner-scoped), so the assessment runs in CI without
// credentials and without spending money.
//
// The output is a report, not a leaderboard position.
package capability

import (
	"fmt"
	"io"
	"sort"
	"strings"
)

// Grade is a suite result.
type Grade struct {
	Name    string
	Passed  int
	Failed  int
	Skipped int
	// Scope states what the suite does and does not cover. A pass rate
	// without a scope is not evidence of anything.
	Scope string
	// HeldOut marks a suite whose cases must never be tuned against.
	HeldOut bool
}

// Rate returns the pass rate over the cases that ran.
func (g Grade) Rate() float64 {
	ran := g.Passed + g.Failed
	if ran == 0 {
		return 0
	}
	return float64(g.Passed) / float64(ran)
}

// Passed reports whether every case that ran passed.
func (g Grade) AllPassed() bool { return g.Failed == 0 && g.Passed > 0 }

// Report is the full assessment.
type Report struct {
	Grades []Grade
}

// Add records a suite result.
func (r *Report) Add(g Grade) { r.Grades = append(r.Grades, g) }

// Rate returns the overall pass rate across suites.
//
// Weighted by case count, so a suite with three cases cannot outvote a suite
// with four hundred.
func (r *Report) Rate() float64 {
	var passed, ran int
	for _, g := range r.Grades {
		passed += g.Passed
		ran += g.Passed + g.Failed
	}
	if ran == 0 {
		return 0
	}
	return float64(passed) / float64(ran)
}

// Totals returns the case counts.
func (r *Report) Totals() (passed, failed, skipped int) {
	for _, g := range r.Grades {
		passed += g.Passed
		failed += g.Failed
		skipped += g.Skipped
	}
	return
}

// Complete reports whether every suite ran and passed.
func (r *Report) Complete() bool {
	for _, g := range r.Grades {
		if !g.AllPassed() {
			return false
		}
	}
	return len(r.Grades) > 0
}

// Render writes the report. The format is deliberately boring: a table of
// what ran, what passed, and what each suite covers. No aggregate score.
func (r *Report) Render(w io.Writer) {
	total := len(r.Grades)
	passed := 0
	for i := range r.Grades {
		if r.Grades[i].AllPassed() {
			passed++
		}
	}
	tp, tf, ts := r.Totals()

	fmt.Fprintf(w, "capability assessment: %d/%d suites green\n", passed, total)
	fmt.Fprintf(w, "cases: %d passed, %d failed, %d skipped\n", tp, tf, ts)
	if r.Complete() {
		fmt.Fprintf(w, "status: all measured suites green\n")
	} else {
		fmt.Fprintf(w, "status: NOT all suites green\n")
	}
	fmt.Fprintln(w)

	names := make([]string, 0, len(r.Grades))
	for _, g := range r.Grades {
		names = append(names, g.Name)
	}
	sort.Strings(names)

	for _, name := range names {
		g := Grade{}
		for _, candidate := range r.Grades {
			if candidate.Name == name {
				g = candidate
				break
			}
		}
		mark := "PASS"
		if !g.AllPassed() {
			mark = "FAIL"
		}
		if g.HeldOut {
			mark += " (held-out)"
		}
		fmt.Fprintf(w, "  %-4s %-34s %3d/%-3d\n", mark, g.Name, g.Passed, g.Passed+g.Failed)
		fmt.Fprintf(w, "        %s\n", g.Scope)
	}
	fmt.Fprintln(w)
	fmt.Fprintf(w, "no single score is reported by design: each suite covers a\n")
	fmt.Fprintf(w, "different surface, and a weighted average would hide that.\n")
	fmt.Fprintf(w, "see docs/CAPABILITY.md for what is and is not measured.\n")
}

// Format implements fmt.Stringer for logs.
func (r *Report) String() string {
	var b strings.Builder
	r.Render(&b)
	return b.String()
}
