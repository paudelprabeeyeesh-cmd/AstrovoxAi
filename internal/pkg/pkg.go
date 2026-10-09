// Package pkg provides a package manager: registry, dependency
// resolution, install/uninstall, and lockfiles.
package pkg

import (
	"errors"
	"fmt"
	"sort"
	"strings"
	"sync"
)

// SemanticVersion is a semver-like version.
type SemanticVersion struct {
	Major int
	Minor int
	Patch int
	Pre   string
}

// ParseVersion parses "1.2.3-pre" (pre is optional).
func ParseVersion(s string) (SemanticVersion, error) {
	var v SemanticVersion
	pre := ""
	if i := strings.IndexByte(s, '-'); i >= 0 {
		pre = s[i+1:]
		s = s[:i]
	}
	n, err := fmt.Sscanf(s, "%d.%d.%d", &v.Major, &v.Minor, &v.Patch)
	if err != nil || n != 3 {
		return v, fmt.Errorf("invalid version %q", s)
	}
	v.Pre = pre
	return v, nil
}

// String renders the version.
func (v SemanticVersion) String() string {
	s := fmt.Sprintf("%d.%d.%d", v.Major, v.Minor, v.Patch)
	if v.Pre != "" {
		s += "-" + v.Pre
	}
	return s
}

// Compare returns -1, 0 or 1.
func (v SemanticVersion) Compare(o SemanticVersion) int {
	if v.Major != o.Major {
		if v.Major < o.Major {
			return -1
		}
		return 1
	}
	if v.Minor != o.Minor {
		if v.Minor < o.Minor {
			return -1
		}
		return 1
	}
	if v.Patch != o.Patch {
		if v.Patch < o.Patch {
			return -1
		}
		return 1
	}
	if v.Pre == o.Pre {
		return 0
	}
	if v.Pre == "" {
		return 1 // release > prerelease
	}
	if o.Pre == "" {
		return -1
	}
	return strings.Compare(v.Pre, o.Pre)
}

// Constraint is a version constraint like ">=1.2.0".
type Constraint struct {
	Op      string
	Version SemanticVersion
}

// ParseConstraint parses a constraint such as ">=1.2.3".
func ParseConstraint(s string) (Constraint, error) {
	s = strings.TrimSpace(s)
	var c Constraint
	for _, op := range []string{">=", "<=", "==", "!=", "~>", ">", "<", "^", "~", "="} {
		if strings.HasPrefix(s, op) {
			c.Op = op
			v, err := ParseVersion(strings.TrimSpace(s[len(op):]))
			if err != nil {
				return c, err
			}
			c.Version = v
			return c, nil
		}
	}
	v, err := ParseVersion(s)
	if err != nil {
		return c, err
	}
	c.Op = "=="
	c.Version = v
	return c, nil
}

// Matches reports whether a version satisfies the constraint.
func (c Constraint) Matches(v SemanticVersion) bool {
	cmp := v.Compare(c.Version)
	switch c.Op {
	case ">=", "=>":
		return cmp >= 0
	case "<=", "=<":
		return cmp <= 0
	case "==", "=":
		return cmp == 0
	case "!=":
		return cmp != 0
	case ">":
		return cmp > 0
	case "<":
		return cmp < 0
	case "^":
		return cmp >= 0 && v.Major == c.Version.Major
	case "~>", "~":
		return cmp >= 0 && v.Major == c.Version.Major && v.Minor == c.Version.Minor
	default:
		return false
	}
}

// String renders the constraint.
func (c Constraint) String() string { return c.Op + c.Version.String() }

// Dependency is a required package with a version constraint.
type Dependency struct {
	Name       string
	Constraint Constraint
	Optional   bool
}

// Package is a package definition.
type Package struct {
	Name         string
	Version      SemanticVersion
	Description  string
	Author       string
	License      string
	Repository   string
	Dependencies []Dependency
	Executables  []string
	Checksum     string
}

// Release is a concrete published version of a package.
type Release struct {
	Package Package
	Files   map[string][]byte
}

// Registry stores packages and their releases.
type Registry struct {
	mu       sync.RWMutex
	releases map[string][]Release // name -> sorted releases
	owners   map[string][]string
}

// NewRegistry creates a registry.
func NewRegistry() *Registry {
	return &Registry{
		releases: make(map[string][]Release),
		owners:   make(map[string][]string),
	}
}

// Publish publishes a release.
func (r *Registry) Publish(rel Release) error {
	if rel.Package.Name == "" {
		return errors.New("package name required")
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	existing := r.releases[rel.Package.Name]
	for _, e := range existing {
		if e.Package.Version.Compare(rel.Package.Version) == 0 {
			return fmt.Errorf("version %s already published", rel.Package.Version)
		}
	}
	existing = append(existing, rel)
	sort.Slice(existing, func(i, j int) bool {
		return existing[i].Package.Version.Compare(existing[j].Package.Version) > 0
	})
	r.releases[rel.Package.Name] = existing
	return nil
}

// Versions returns all published versions of a package (newest first).
func (r *Registry) Versions(name string) []SemanticVersion {
	r.mu.RLock()
	defer r.mu.RUnlock()
	rels := r.releases[name]
	out := make([]SemanticVersion, 0, len(rels))
	for _, e := range rels {
		out = append(out, e.Package.Version)
	}
	return out
}

// Get returns the release matching a constraint.
func (r *Registry) Get(name string, c Constraint) (*Release, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	rels := r.releases[name]
	for _, e := range rels {
		if c.Matches(e.Package.Version) {
			r := e
			return &r, nil
		}
	}
	return nil, fmt.Errorf("no version of %s matches %s", name, c)
}

// Search searches packages whose name or description matches.
func (r *Registry) Search(query string) []Package {
	r.mu.RLock()
	defer r.mu.RUnlock()
	q := strings.ToLower(query)
	var out []Package
	for name, rels := range r.releases {
		for _, e := range rels {
			if strings.Contains(strings.ToLower(name), q) ||
				strings.Contains(strings.ToLower(e.Package.Description), q) {
				out = append(out, e.Package)
				break
			}
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out
}

// Count returns the number of packages.
func (r *Registry) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.releases)
}

// Resolve resolves a dependency set to concrete versions using
// backtracking-free greedy resolution (newest matching first).
func (r *Registry) Resolve(deps []Dependency) (map[string]SemanticVersion, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	resolved := make(map[string]SemanticVersion)
	var visit func(d Dependency) error
	visiting := map[string]bool{}

	visit = func(d Dependency) error {
		if v, ok := resolved[d.Name]; ok {
			if !d.Constraint.Matches(v) {
				return fmt.Errorf("dependency conflict: %s %s does not satisfy %s", d.Name, v, d.Constraint)
			}
			return nil
		}
		if visiting[d.Name] {
			return fmt.Errorf("circular dependency on %s", d.Name)
		}
		visiting[d.Name] = true
		defer delete(visiting, d.Name)

		rels := r.releases[d.Name]
		for _, e := range rels {
			if !d.Constraint.Matches(e.Package.Version) {
				continue
			}
			// tentatively resolve
			for _, dep := range e.Package.Dependencies {
				if err := visit(dep); err != nil {
					continue
				}
			}
			resolved[d.Name] = e.Package.Version
			return nil
		}
		return fmt.Errorf("cannot resolve %s %s", d.Name, d.Constraint)
	}

	for _, d := range deps {
		if err := visit(d); err != nil {
			return nil, err
		}
	}
	return resolved, nil
}

// InstalledPackage is a package installed locally.
type InstalledPackage struct {
	Package
	Files map[string][]byte
}

// Manager installs packages from a registry.
type Manager struct {
	registry   *Registry
	mu         sync.RWMutex
	installed  map[string]InstalledPackage
	lockfile   Lockfile
	root       string
}

// Lockfile records resolved versions.
type Lockfile struct {
	Packages map[string]SemanticVersion
}

// NewManager creates a package manager.
func NewManager(reg *Registry, root string) *Manager {
	return &Manager{
		registry:  reg,
		installed: make(map[string]InstalledPackage),
		lockfile:  Lockfile{Packages: make(map[string]SemanticVersion)},
		root:      root,
	}
}

// Registry returns the manager's registry.
func (m *Manager) Registry() *Registry { return m.registry }

// Install resolves and installs a package with its dependencies.
func (m *Manager) Install(name string, c Constraint) error {
	resolved, err := m.registry.Resolve([]Dependency{{Name: name, Constraint: c}})
	if err != nil {
		return err
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	for dep, ver := range resolved {
		rel, err := m.registry.Get(dep, Constraint{Op: "==", Version: ver})
		if err != nil {
			return err
		}
		m.installed[dep] = InstalledPackage{
			Package: rel.Package,
			Files:   rel.Files,
		}
		m.lockfile.Packages[dep] = ver
	}
	return nil
}

// Uninstall removes a package.
func (m *Manager) Uninstall(name string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.installed[name]; !ok {
		return fmt.Errorf("%s is not installed", name)
	}
	delete(m.installed, name)
	delete(m.lockfile.Packages, name)
	return nil
}

// Installed returns the names of installed packages.
func (m *Manager) Installed() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	names := make([]string, 0, len(m.installed))
	for n := range m.installed {
		names = append(names, n)
	}
	sort.Strings(names)
	return names
}

// Get returns an installed package.
func (m *Manager) Get(name string) (*InstalledPackage, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	p, ok := m.installed[name]
	return &p, ok
}

// Lockfile returns the current lockfile.
func (m *Manager) LockfileData() Lockfile {
	m.mu.RLock()
	defer m.mu.RUnlock()
	pkgs := make(map[string]SemanticVersion, len(m.lockfile.Packages))
	for k, v := range m.lockfile.Packages {
		pkgs[k] = v
	}
	return Lockfile{Packages: pkgs}
}

// Verify recomputes checksums of installed packages.
func (m *Manager) Verify() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	var bad []string
	for name, p := range m.installed {
		if p.Checksum != "" {
			sum := computeChecksum(p.Files)
			if sum != p.Checksum {
				bad = append(bad, name)
			}
		}
	}
	sort.Strings(bad)
	return bad
}

// computeChecksum is a simple deterministic content hash.
func computeChecksum(files map[string][]byte) string {
	names := make([]string, 0, len(files))
	for n := range files {
		names = append(names, n)
	}
	sort.Strings(names)
	var h uint64 = 14695981039346656037 // FNV-1a offset basis
	for _, n := range names {
		for i := 0; i < len(n); i++ {
			h ^= uint64(n[i])
			h *= 1099511628211
		}
		for _, b := range files[n] {
			h ^= uint64(b)
			h *= 1099511628211
		}
	}
	hex := "0123456789abcdef"
	out := make([]byte, 16)
	for i := 15; i >= 0; i-- {
		out[i] = hex[h&0xf]
		h >>= 4
	}
	return string(out)
}