// Package pluginx provides plugin version compatibility checking and a
// marketplace manifest format.
package pluginx

import (
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strings"

	"github.com/astrovox/astrovox/internal/pkg"
)

// Compatibility errors.
var (
	ErrIncompatible    = errors.New("incompatible plugin")
	ErrUnsupportedHost = errors.New("unsupported host version")
)

// SemVer is a semantic version.
type SemVer struct {
	Major, Minor, Patch int
}

// ParseSemVer parses "major.minor.patch".
func ParseSemVer(s string) (SemVer, error) {
	var v SemVer
	n, err := fmt.Sscanf(s, "%d.%d.%d", &v.Major, &v.Minor, &v.Patch)
	if err != nil || n != 3 {
		return v, fmt.Errorf("invalid semver %q", s)
	}
	return v, nil
}

// String renders the version.
func (v SemVer) String() string { return fmt.Sprintf("%d.%d.%d", v.Major, v.Minor, v.Patch) }

// Compare returns -1, 0 or 1.
func (v SemVer) Compare(o SemVer) int {
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
	return 0
}

// CompatRange is a host version compatibility range: [Min, Max).
type CompatRange struct {
	Min SemVer
	Max SemVer
}

// Contains reports whether a version is in [Min, Max).
func (r CompatRange) Contains(v SemVer) bool {
	return v.Compare(r.Min) >= 0 && v.Compare(r.Max) < 0
}

// String renders "major.minor.patch - major.minor.patch".
func (r CompatRange) String() string { return r.Min.String() + " - " + r.Max.String() }

// PluginAPI records the API functions a plugin expects.
type PluginAPI struct {
	Version string   `json:"version"`
	Functions []string `json:"functions"`
}

// Manifest is a plugin marketplace manifest.
type Manifest struct {
	Name         string   `json:"name"`
	Description  string   `json:"description"`
	Author       string   `json:"author"`
	License      string   `json:"license"`
	Homepage     string   `json:"homepage,omitempty"`
	Version      string   `json:"version"`
	APIVersion   string   `json:"api_version"`
	HostRange    []string `json:"host_compatibility,omitempty"`
	Capabilities []string `json:"capabilities,omitempty"`
	Dependencies []Dependency `json:"dependencies,omitempty"`
	Entrypoint   string   `json:"entrypoint"`
	WASM         bool     `json:"wasm,omitempty"`
	Checksum     string   `json:"checksum,omitempty"`
	Screenshots  []string `json:"screenshots,omitempty"`
	Tags         []string `json:"tags,omitempty"`
	Downloads    int64    `json:"downloads,omitempty"`
	Rating       float64  `json:"rating,omitempty"`
}

// Dependency is a runtime dependency requirement.
type Dependency struct {
	Name       string `json:"name"`
	Constraint string `json:"constraint"`
}

// Validate checks that the manifest is well-formed.
func (m *Manifest) Validate() error {
	if m.Name == "" {
		return errors.New("manifest requires a name")
	}
	if m.Entrypoint == "" {
		return errors.New("manifest requires an entrypoint")
	}
	if _, err := ParseSemVer(m.Version); err != nil {
		return fmt.Errorf("bad plugin version: %w", err)
	}
	if _, err := ParseSemVer(m.APIVersion); err != nil {
		return fmt.Errorf("bad api version: %w", err)
	}
	for _, r := range m.HostRange {
		parts := strings.Split(r, " - ")
		if len(parts) != 2 {
			return fmt.Errorf("bad host_compatibility entry %q", r)
		}
		if _, err := ParseSemVer(strings.TrimSpace(parts[0])); err != nil {
			return err
		}
		if _, err := ParseSemVer(strings.TrimSpace(parts[1])); err != nil {
			return err
		}
	}
	return nil
}

// Encode marshals a manifest to canonical JSON.
func (m *Manifest) Encode() ([]byte, error) {
	m.Tags = sortedCopy(m.Tags)
	m.Capabilities = sortedCopy(m.Capabilities)
	return json.MarshalIndent(m, "", "  ")
}

func sortedCopy(in []string) []string {
	if len(in) == 0 {
		return nil
	}
	out := append([]string(nil), in...)
	sort.Strings(out)
	return out
}

// Compatibility evaluates whether a plugin can load in a host.
type Compatibility struct {
	hostVersion SemVer
	apiVersion  SemVer
	history     []string
}

// NewCompatibility creates a compatibility checker for a host build.
func NewCompatibility(hostVersion, apiVersion string) (*Compatibility, error) {
	h, err := ParseSemVer(hostVersion)
	if err != nil {
		return nil, fmt.Errorf("host version: %w", err)
	}
	a, err := ParseSemVer(apiVersion)
	if err != nil {
		return nil, fmt.Errorf("api version: %w", err)
	}
	return &Compatibility{hostVersion: h, apiVersion: a}, nil
}

// HostVersion returns the host version.
func (c *Compatibility) HostVersion() SemVer { return c.hostVersion }

// APIVersion returns the host API version.
func (c *Compatibility) APIVersion() SemVer { return c.apiVersion }

// Check evaluates a manifest against the host.
func (c *Compatibility) Check(m *Manifest) error {
	if m == nil {
		return errors.New("nil manifest")
	}
	if err := m.Validate(); err != nil {
		return err
	}
	if len(m.HostRange) == 0 {
		// No constraint recorded: accept, but record it.
		c.history = append(c.history, fmt.Sprintf("%s: no host constraint (assumed ok)", m.Name))
		return nil
	}
	for _, r := range m.HostRange {
		lo, hi, err := parseRange(r)
		if err != nil {
			return err
		}
		if (CompatRange{Min: lo, Max: hi}).Contains(c.hostVersion) {
			return nil
		}
		c.history = append(c.history, fmt.Sprintf("%s: rejected by range %s", m.Name, r))
	}
	return fmt.Errorf("%w: %s supports host %v, host is %s",
		ErrUnsupportedHost, m.Name, m.HostRange, c.hostVersion)
}

// CheckAPI reports whether the plugin's API version matches the host's.
func (c *Compatibility) CheckAPI(m *Manifest) error {
	api, err := ParseSemVer(m.APIVersion)
	if err != nil {
		return err
	}
	if api.Major != c.apiVersion.Major {
		return fmt.Errorf("%w: plugin api %s, host api %s (major mismatch)",
			ErrIncompatible, api, c.apiVersion)
	}
	if api.Minor > c.apiVersion.Minor {
		return fmt.Errorf("%w: plugin api %s newer than host api %s",
			ErrIncompatible, api, c.apiVersion)
	}
	return nil
}

// Full performs both host-range and API checks.
func (c *Compatibility) Full(m *Manifest) error {
	if err := c.Check(m); err != nil {
		return err
	}
	return c.CheckAPI(m)
}

func parseRange(s string) (SemVer, SemVer, error) {
	parts := strings.Split(s, "-")
	if len(parts) != 2 {
		return SemVer{}, SemVer{}, fmt.Errorf("bad range %q", s)
	}
	lo, err := ParseSemVer(strings.TrimSpace(parts[0]))
	if err != nil {
		return SemVer{}, SemVer{}, err
	}
	hi, err := ParseSemVer(strings.TrimSpace(parts[1]))
	if err != nil {
		return SemVer{}, SemVer{}, err
	}
	return lo, hi, nil
}

// ResolveManifestDependencies resolves a manifest's dependencies using
// the package manager's resolver.
func ResolveManifestDependencies(m *Manifest) (map[string]pkg.SemanticVersion, error) {
	if m == nil {
		return nil, errors.New("nil manifest")
	}
	deps := make([]pkg.Dependency, 0, len(m.Dependencies))
	for _, d := range m.Dependencies {
		c, err := pkg.ParseConstraint(d.Constraint)
		if err != nil {
			return nil, fmt.Errorf("dependency %s: %w", d.Name, err)
		}
		deps = append(deps, pkg.Dependency{Name: d.Name, Constraint: c})
	}
	return pkg.NewRegistry().Resolve(deps)
}

// Marketplace is a searchable index of plugin manifests.
type Marketplace struct {
	entries map[string]*Manifest
}

// NewMarketplace creates a marketplace.
func NewMarketplace() *Marketplace {
	return &Marketplace{entries: make(map[string]*Manifest)}
}

// Publish indexes a manifest.
func (m *Marketplace) Publish(man *Manifest) error {
	if man == nil {
		return errors.New("nil manifest")
	}
	if err := man.Validate(); err != nil {
		return err
	}
	m.entries[man.Name] = man
	return nil
}

// Get returns a manifest by name.
func (m *Marketplace) Get(name string) (*Manifest, bool) {
	man, ok := m.entries[name]
	return man, ok
}

// List returns all manifest names.
func (m *Marketplace) List() []string {
	names := make([]string, 0, len(m.entries))
	for n := range m.entries {
		names = append(names, n)
	}
	sort.Strings(names)
	return names
}

// Search finds manifests whose name, description or tags match a query.
func (m *Marketplace) Search(query string) []*Manifest {
	q := strings.ToLower(query)
	var res []*Manifest
	for _, man := range m.entries {
		if strings.Contains(strings.ToLower(man.Name), q) ||
			strings.Contains(strings.ToLower(man.Description), q) {
			res = append(res, man)
			continue
		}
		for _, t := range man.Tags {
			if strings.Contains(strings.ToLower(t), q) {
				res = append(res, man)
				break
			}
		}
	}
	sort.Slice(res, func(i, j int) bool { return res[i].Name < res[j].Name })
	return res
}

// Count returns the number of indexed manifests.
func (m *Marketplace) Count() int { return len(m.entries) }