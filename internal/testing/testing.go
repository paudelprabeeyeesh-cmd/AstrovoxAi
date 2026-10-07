package testing

import (
	"os"
	"runtime"
	"strings"
)

// RuntimeInfo returns basic runtime information.
func RuntimeInfo() map[string]string {
	return map[string]string{
		"go_version": runtime.Version(),
		"os":         runtime.GOOS,
		"arch":       runtime.GOARCH,
	}
}

// EnvWithPrefix returns environment variables with the given prefix,
// keyed by their full variable names.
func EnvWithPrefix(prefix string) map[string]string {
	env := make(map[string]string)
	for _, entry := range os.Environ() {
		key, value, ok := strings.Cut(entry, "=")
		if ok && strings.HasPrefix(key, prefix) {
			env[key] = value
		}
	}
	return env
}
