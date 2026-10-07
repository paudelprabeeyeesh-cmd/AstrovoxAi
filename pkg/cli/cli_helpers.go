package cli

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"runtime"
	"strings"
	"time"
)

// ProgressBar represents a simple terminal progress indicator.
type ProgressBar struct {
	total   int
	current int
	width   int
	out     io.Writer
}

// NewProgressBar creates a new progress bar.
func NewProgressBar(total int, out io.Writer) *ProgressBar {
	if out == nil {
		out = os.Stdout
	}
	return &ProgressBar{total: total, width: 40, out: out}
}

// SetProgress updates the current progress.
func (p *ProgressBar) SetProgress(current int) {
	p.current = current
	p.render()
}

// render draws the progress bar.
func (p *ProgressBar) render() {
	percent := 0.0
	if p.total > 0 {
		percent = float64(p.current) / float64(p.total)
	}
	filled := int(percent * float64(p.width))
	bar := strings.Repeat("=", filled) + strings.Repeat("-", p.width-filled)
	fmt.Fprintf(p.out, "\r[%s] %d%%", bar, int(percent*100))
	if p.current >= p.total {
		fmt.Fprintln(p.out)
	}
}

// ColoredWriter wraps an io.Writer with ANSI color support.
type ColoredWriter struct {
	out io.Writer
}

// NewColoredWriter creates a colored writer.
func NewColoredWriter(out io.Writer) *ColoredWriter {
	return &ColoredWriter{out: out}
}

// Info prints an info message in cyan.
func (c *ColoredWriter) Info(msg string) {
	fmt.Fprintf(c.out, "\033[36mINFO:\033[0m %s\n", msg)
}

// Warn prints a warning message in yellow.
func (c *ColoredWriter) Warn(msg string) {
	fmt.Fprintf(c.out, "\033[33mWARN:\033[0m %s\n", msg)
}

// Error prints an error message in red.
func (c *ColoredWriter) Error(msg string) {
	fmt.Fprintf(c.out, "\033[31mERROR:\033[0m %s\n", msg)
}

// Success prints a success message in green.
func (c *ColoredWriter) Success(msg string) {
	fmt.Fprintf(c.out, "\033[32mOK:\033[0m %s\n", msg)
}

// ShellCompletion generates shell completion scripts.
type ShellCompletion struct{}

// NewShellCompletion creates a new completion helper.
func NewShellCompletion() *ShellCompletion {
	return &ShellCompletion{}
}

// ForBash returns a bash completion script.
func (s *ShellCompletion) ForBash() string {
	return `#!/bin/bash
_complete_astrovox() {
  local cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=($(compgen -W "init train infer benchmark profile graph plugin doctor export" -- "${cur}"))
}
complete -F _complete_astrovox astrovox
`
}

// ForZsh returns a zsh completion script.
func (s *ShellCompletion) ForZsh() string {
	return "#compdef astrovox\n" +
		"_astrovox() {\n  local -a cmds\n  cmds=(init train infer benchmark profile graph plugin doctor export)\n  _describe -t commands 'astrovox command' cmds\n" +
		"}\n"
}

// CommandConfig groups commonly used CLI flags.
type CommandConfig struct {
	Name        string
	Description string
	Flags       map[string]string
	Action      func([]string) error
}

// JSONOutput writes data as formatted JSON.
func JSONOutput(w io.Writer, v interface{}) error {
	encoder := json.NewEncoder(w)
	encoder.SetIndent("", "  ")
	return encoder.Encode(v)
}

// TimedAction measures execution time of a function.
func TimedAction(name string, action func() error) error {
	start := time.Now()
	err := action()
	elapsed := time.Since(start)
	if err != nil {
		return fmt.Errorf("%s failed after %s: %w", name, elapsed, err)
	}
	fmt.Printf("%s completed in %s\n", name, elapsed)
	return nil
}

// RuntimeInfo returns basic runtime information.
func RuntimeInfo() map[string]string {
	return map[string]string{
		"go_version": runtime.Version(),
		"os":         runtime.GOOS,
		"arch":       runtime.GOARCH,
		"cpus":       fmt.Sprintf("%d", runtime.NumCPU()),
	}
}

// EnvWithPrefix returns env vars with a given prefix.
func EnvWithPrefix(prefix string) map[string]string {
	env := make(map[string]string)
	for _, e := range os.Environ() {
		parts := strings.SplitN(e, "=", 2)
		if len(parts) != 2 {
			continue
		}
		if strings.HasPrefix(parts[0], prefix) {
			env[parts[0]] = parts[1]
		}
	}
	return env
}
