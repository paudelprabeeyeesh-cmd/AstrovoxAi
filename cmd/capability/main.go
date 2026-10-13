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
	"strings"

	"github.com/astrovox/astrovox/internal/api/capability"
)

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
}

// suites is the measured set. Every entry has a scope, because a pass rate
// with no scope is a number with nothing behind it.

// runGoTest runs a package and returns its raw JSON output.
//
// The working directory is found by walking up to the go.mod, so the
// command works from anywhere in the tree rather than assuming it was
// invoked from cmd/capability.
func runGoTest(pkg string) (string, error) {
	root, err := moduleRoot()
	if err != nil {
		return "", err
	}
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
func grade(s suite) capability.Grade {
	out, err := runGoTest(s.pkg)
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

func main() {
	asJSON := flag.Bool("json", false, "emit the report as JSON")
	flag.Parse()

	report := &capability.Report{}
	for _, s := range suites {
		report.Add(grade(s))
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
