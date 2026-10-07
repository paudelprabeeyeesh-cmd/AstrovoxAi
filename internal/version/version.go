// Package version implements semantic versioning (semver 2.0): parsing,
// comparison, constraint solving, plus runtime environment reporting and
// environment-variable loading.
package version

import (
	"fmt"
	"os"
	"runtime"
	"sort"
	"strconv"
	"strings"

	"github.com/astrovox/astrovox/internal/errors"
)

// Version is an immutable semantic version.
type Version struct {
	Major      uint64
	Minor      uint64
	Patch      uint64
	Prerelease string
	Build      string
}

// Parse parses a semantic version string.
func Parse(s string) (Version, error) {
	orig := s
	if i := strings.IndexByte(s, '+'); i >= 0 {
		s = s[:i] + "|" + s[i+1:]
	}
	var build string
	if i := strings.IndexByte(s, '|'); i >= 0 {
		build = s[i+1:]
		s = s[:i]
	}
	prerelease := ""
	if i := strings.IndexByte(s, '-'); i >= 0 {
		prerelease = s[i+1:]
		s = s[:i]
	}
	parts := strings.Split(s, ".")
	if len(parts) != 3 {
		return Version{}, errors.New(errors.CodeInvalidArgument, "version must have 3 numeric parts").
			WithField("version", orig)
	}
	v := Version{Prerelease: prerelease, Build: build}
	for i, p := range parts {
		n, err := parseUint(p)
		if err != nil {
			return Version{}, errors.Wrap(err, errors.CodeInvalidArgument, "non-numeric version part").
				WithField("part", p)
		}
		switch i {
		case 0:
			v.Major = n
		case 1:
			v.Minor = n
		case 2:
			v.Patch = n
		}
	}
	return v, nil
}

func parseUint(s string) (uint64, error) {
	if s == "" {
		return 0, errors.New(errors.CodeInvalidArgument, "empty numeric part")
	}
	if len(s) > 1 && s[0] == '0' {
		return 0, errors.New(errors.CodeInvalidArgument, "leading zeros not allowed")
	}
	n, err := strconv.ParseUint(s, 10, 64)
	if err != nil {
		return 0, err
	}
	return n, nil
}

// Compare returns -1, 0, or 1 per semver precedence rules.
func (v Version) Compare(o Version) int {
	if v.Major != o.Major {
		return cmpUint(v.Major, o.Major)
	}
	if v.Minor != o.Minor {
		return cmpUint(v.Minor, o.Minor)
	}
	if v.Patch != o.Patch {
		return cmpUint(v.Patch, o.Patch)
	}
	return comparePrerelease(v.Prerelease, o.Prerelease)
}

func cmpUint(a, b uint64) int {
	if a < b {
		return -1
	}
	if a > b {
		return 1
	}
	return 0
}

func comparePrerelease(a, b string) int {
	if a == b {
		return 0
	}
	if a == "" {
		return 1
	}
	if b == "" {
		return -1
	}
	ap := strings.Split(a, ".")
	bp := strings.Split(b, ".")
	for i := 0; i < len(ap) && i < len(bp); i++ {
		if c := comparePrereleaseID(ap[i], bp[i]); c != 0 {
			return c
		}
	}
	return cmpInt(len(ap), len(bp))
}

func comparePrereleaseID(a, b string) int {
	an, aerr := strconv.ParseUint(a, 10, 64)
	bn, berr := strconv.ParseUint(b, 10, 64)
	if aerr == nil && berr == nil {
		return cmpUint(an, bn)
	}
	if aerr == nil {
		return -1
	}
	if berr == nil {
		return 1
	}
	return strings.Compare(a, b)
}

func cmpInt(a, b int) int {
	if a < b {
		return -1
	}
	if a > b {
		return 1
	}
	return 0
}

// String renders the canonical semver string.
func (v Version) String() string {
	s := fmt.Sprintf("%d.%d.%d", v.Major, v.Minor, v.Patch)
	if v.Prerelease != "" {
		s += "-" + v.Prerelease
	}
	if v.Build != "" {
		s += "+" + v.Build
	}
	return s
}

// MajorVersion returns the MAJOR-only version.
func (v Version) MajorVersion() Version { return Version{Major: v.Major} }

// Compatible reports whether o is within the same MAJOR version (semver
// compatibility rule).
func (v Version) Compatible(o Version) bool { return v.Major == o.Major }

// Constraint is a parsed version constraint expression.
type Constraint struct {
	Raw     string
	checks  []func(Version) bool
}

// ParseConstraint parses constraint expressions: "1.2.3", "^1.2.0", "~1.2.0",
// ">=1.0.0", "<=2.0.0", ">1.0.0", "<2.0.0", "=1.2.3", and comma-separated
// conjunctions.
func ParseConstraint(expr string) (Constraint, error) {
	expr = strings.TrimSpace(expr)
	if expr == "" {
		return Constraint{}, errors.New(errors.CodeInvalidArgument, "empty constraint")
	}
	parts := strings.Split(expr, ",")
	c := Constraint{Raw: expr}
	for _, part := range parts {
		part = strings.TrimSpace(part)
		fn, err := parseSingle(part)
		if err != nil {
			return Constraint{}, err
		}
		c.checks = append(c.checks, fn)
	}
	return c, nil
}

func parseSingle(part string) (func(Version) bool, error) {
	switch {
	case strings.HasPrefix(part, "^"):
		v, err := Parse(part[1:])
		if err != nil {
			return nil, err
		}
		return func(o Version) bool {
			return o.Major == v.Major && o.Compare(v) >= 0 &&
				(v.Major > 0 || o.Minor == v.Minor) &&
				(v.Major > 0 || v.Minor > 0 || o.Patch == v.Patch)
		}, nil
	case strings.HasPrefix(part, "~"):
		v, err := Parse(part[1:])
		if err != nil {
			return nil, err
		}
		return func(o Version) bool {
			return o.Major == v.Major && o.Minor == v.Minor && o.Compare(v) >= 0
		}, nil
	case strings.HasPrefix(part, ">="):
		v, err := Parse(part[2:])
		if err != nil {
			return nil, err
		}
		return func(o Version) bool { return o.Compare(v) >= 0 }, nil
	case strings.HasPrefix(part, "<="):
		v, err := Parse(part[2:])
		if err != nil {
			return nil, err
		}
		return func(o Version) bool { return o.Compare(v) <= 0 }, nil
	case strings.HasPrefix(part, ">"):
		v, err := Parse(part[1:])
		if err != nil {
			return nil, err
		}
		return func(o Version) bool { return o.Compare(v) > 0 }, nil
	case strings.HasPrefix(part, "<"):
		v, err := Parse(part[1:])
		if err != nil {
			return nil, err
		}
		return func(o Version) bool { return o.Compare(v) < 0 }, nil
	case strings.HasPrefix(part, "="):
		v, err := Parse(part[1:])
		if err != nil {
			return nil, err
		}
		return func(o Version) bool { return o.Compare(v) == 0 }, nil
	default:
		v, err := Parse(part)
		if err != nil {
			return nil, err
		}
		return func(o Version) bool {
			return o.Major == v.Major && o.Minor == v.Minor && o.Patch == v.Patch
		}, nil
	}
}

// Allows reports whether the version satisfies the constraint.
func (c Constraint) Allows(v Version) bool {
	for _, check := range c.checks {
		if !check(v) {
			return false
		}
	}
	return true
}

// MaxSatisfying returns the highest version in versions that satisfies c.
func (c Constraint) MaxSatisfying(versions []Version) (Version, bool) {
	var candidates []Version
	for _, v := range versions {
		if c.Allows(v) {
			candidates = append(candidates, v)
		}
	}
	if len(candidates) == 0 {
		return Version{}, false
	}
	sort.Slice(candidates, func(i, j int) bool { return candidates[i].Compare(candidates[j]) < 0 })
	return candidates[len(candidates)-1], true
}

// Environment describes the running system for compatibility reporting.
type Environment struct {
	GoVersion string `json:"go_version"`
	GOOS      string `json:"goos"`
	GOARCH    string `json:"goarch"`
	NumCPU    int    `json:"num_cpu"`
	GOMAXPROCS int   `json:"gomaxprocs"`
}

// CurrentEnvironment captures the runtime environment.
func CurrentEnvironment() Environment {
	return Environment{
		GoVersion:  runtime.Version(),
		GOOS:       runtime.GOOS,
		GOARCH:     runtime.GOARCH,
		NumCPU:     runtime.NumCPU(),
		GOMAXPROCS: runtime.GOMAXPROCS(0),
	}
}

// LoadEnv returns all environment variables whose name starts with prefix,
// with the prefix stripped and lowercased. Double underscores map to dots.
func LoadEnv(prefix string) map[string]string {
	out := map[string]string{}
	for _, kv := range os.Environ() {
		eq := strings.IndexByte(kv, '=')
		if eq < 0 {
			continue
		}
		name, val := kv[:eq], kv[eq+1:]
		if !strings.HasPrefix(name, prefix) {
			continue
		}
		key := strings.ToLower(strings.TrimPrefix(name, prefix))
		key = strings.ReplaceAll(key, "__", ".")
		out[key] = val
	}
	return out
}

// EnvOr returns the environment variable or the fallback.
func EnvOr(name, fallback string) string {
	if v, ok := os.LookupEnv(name); ok {
		return v
	}
	return fallback
}
