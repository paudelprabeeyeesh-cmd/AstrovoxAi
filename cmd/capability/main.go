// Command capability runs the capability assessment over the real suite
// counts and prints a report.
//
// It deliberately does not print a single number. It prints which suites
// ran, how many cases passed in each, and what each suite covers, so a
// reader can judge the result rather than trusting a weighted average that
// would hide a suite with no cases in it.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/astrovox/astrovox/internal/api/capability"
)

// Summary-line patterns for pytest, e.g. "12 passed, 1 failed in 3.2s".
var passedRe = regexp.MustCompile(`(\d+) passed`)
var failedRe = regexp.MustCompile(`(\d+) failed`)

// suite describes one measurement. Counts come from the runner, not from
// here, so this command cannot inflate them.
type suite struct {
	name    string
	scope   string
	heldOut bool
	// pkg is the Go package path, run with `go test -json`.
	pkg string
}

// suites is the measured set. Every entry has a scope, because a pass rate
// with no scope is a number with nothing behind it.
var suites = []suite{
	{"security.ssrf", "SSRF guard resolves before connecting and blocks private ranges", false, "./internal/api/ssrf/..."},
	{"security.tokens", "single-use, purpose-scoped, expiring email tokens", false, "./internal/api/mail/..."},
	{"security.idempotency", "retried writes do not execute twice", false, "./internal/api/idempotency/..."},
	{"security.logging", "structured logs redact secrets held in fields of any name", false, "./internal/api/logging/..."},
	{"server.identity", "register, login, verify, reset and magic-link flows", false, "./cmd/api/..."},
	{"server.http", "error envelope, auth chain, tenant scoping on every route", false, "./internal/httpapi/..."},
	{"server.chat", "spend gate runs before the provider call", false, "./internal/chat/..."},
	{"retrieval.acl", "owner is inside the search key, not a post-filter", false, "./internal/retrieval/..."},
	{"memory.policy", "refuses sensitive and instruction-shaped candidates", false, "./internal/memstore/..."},
	{"tools.budget", "arguments validated before execution; loops capped", false, "./internal/tools/..."},
	{"conversations.scoping", "cross-tenant read, write and delete all fail", false, "./internal/conversations/..."},
	{"capability.report", "the assessment itself reports honestly", false, "./internal/api/capability/..."},
	{"engine.ir", "dominance, SSA construction and graph passes", false, "./internal/ir/..."},
	{"engine.runtime", "work-stealing scheduler, NUMA pools, async engine", false, "./internal/runtime/..."},
	{"engine.tokenizer", "BPE encoding, special tokens and sampling", false, "./internal/tokenizer/..."},
	{"engine.serving", "OpenAI-compatible serving surface and model loading", false, "./internal/serving/..."},
	{"engine.errors", "the engine's typed error codes", false, "./internal/errors/..."},
}

// pythonSuites run outside `go test`, so they are invoked directly. Each
// has an explicit scope; a suite with no scope is a number with nothing
// behind it.
var pythonSuites = []struct {
	name  string
	scope string
	args  []string
}{
	{"evals.structure", "the golden task set and its grading harness", []string{"-m", "pytest", "evals", "-q", "--no-header"}},
	{"security.python", "the Python backend's own security tests", []string{"-m", "pytest", "02-Backend/tests/security", "-q", "--no-header", "--timeout=90", "-p", "no:randomly"}},
}

// suites is the measured set. Every entry has a scope, because a pass rate
// with no scope is a number with nothing behind it.

// runGoTest runs a package and returns its raw JSON output.
//
// The working directory is found by walking up to the go.mod, so the
// command works from anywhere in the tree rather than assuming it was
// invoked from cmd/capability.
func runGoTest(pkg, root string) (string, error) {
	cmd := exec.Command("go", "test", pkg, "-count=1", "-json")
	cmd.Dir = root
	out, err := cmd.Output()
	return string(out), err
}

// moduleRoot returns the directory holding go.mod.
func moduleRoot() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return os.Getwd()
		}
		dir = parent
	}
}

// grade runs one suite and returns its grade. The module root is passed in
// grade runs one suite and returns its grade. The module root is passed in
// so a single lookup serves both the Go and the Python runner.
func grade(s suite, root string) capability.Grade {
	out, err := runGoTest(s.pkg, root)
	if out == "" && err != nil {
		log.Printf("suite %s could not run: %v", s.name, err)
		return capability.Grade{
			Name: s.name, Scope: s.scope, HeldOut: s.heldOut,
		}
	}
	g := capability.Grade{Name: s.name, Scope: s.scope, HeldOut: s.heldOut}
	for _, line := range strings.Split(out, "\n") {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "{") {
			continue
		}
		switch parseAction(line) {
		case "pass":
			g.Passed++
		case "fail":
			g.Failed++
		case "skip":
			g.Skipped++
		}
	}
	return g
}

// parseAction reads the Action field from one JSON test line.
func parseAction(line string) string {
	var event map[string]interface{}
	if err := json.Unmarshal([]byte(line), &event); err != nil {
		return ""
	}
	action, _ := event["Action"].(string)
	return action
}

// grade runs one suite and returns its grade.
// runPythonSuite runs a pytest suite and parses the summary line.
func runPythonSuite(name, scope string, args []string, root string) capability.Grade {
	g := capability.Grade{Name: name, Scope: scope}
	cmd := exec.Command("python", args...)
	cmd.Dir = root
	out, err := cmd.CombinedOutput()
	text := string(out)
	// A summary line looks like "N passed, M failed in 1.2s". Parsing it
	// keeps this honest: an unparseable line leaves the counts at zero,
	// which the report treats as failing rather than green.
	for _, line := range strings.Split(text, "\n") {
		if passedRe.FindStringSubmatch(line) != nil {
			g.Passed = atoi(passedRe.FindStringSubmatch(line)[1])
		}
		if failedRe.FindStringSubmatch(line) != nil {
			g.Failed = atoi(failedRe.FindStringSubmatch(line)[1])
		}
	}
	if err != nil && g.Passed+g.Failed == 0 {
		log.Printf("suite %s could not run: %v (%s)", name, err, lastLine(text))
	}
	return g
}

func atoi(s string) int {
	n := 0
	for _, r := range s {
		if r < '0' || r > '9' {
			return n
		}
		n = n*10 + int(r-'0')
	}
	return n
}

func lastLine(s string) string {
	lines := strings.Split(strings.TrimSpace(s), "\n")
	if len(lines) == 0 {
		return ""
	}
	return lines[len(lines)-1]
}

func main() {
	asJSON := flag.Bool("json", false, "emit the report as JSON")
	flag.Parse()

	root, err := moduleRoot()
	if err != nil {
		log.Fatalf("could not find the module root: %v", err)
	}

	report := &capability.Report{}
	for _, s := range suites {
		report.Add(grade(s, root))
	}
	for _, s := range pythonSuites {
		report.Add(runPythonSuite(s.name, s.scope, s.args, root))
	}

	if *asJSON {
		payload, _ := json.MarshalIndent(report, "", "  ")
		fmt.Println(string(payload))
		if !report.Complete() {
			os.Exit(1)
		}
		return
	}

	report.Render(os.Stdout)
	if !report.Complete() {
		os.Exit(1)
	}
}
