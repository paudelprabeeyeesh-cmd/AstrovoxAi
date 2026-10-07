package kernel

// Selector picks the best kernel for a backend and version.
type Selector struct {
	registry *Registry
}

// NewSelector creates a selector.
func NewSelector(reg *Registry) *Selector {
	return &Selector{registry: reg}
}

// Select returns the best matching entry, or nil.
func (s *Selector) Select(entries []*Entry, version string, backend string) *Entry {
	if len(entries) == 0 {
		return nil
	}

	for _, e := range entries {
		if e.Descriptor.Version == version && contains(e.Descriptor.Backends, backend) {
			return e
		}
	}

	for _, e := range entries {
		if e.Descriptor.Version == version {
			return e
		}
	}

	latest := entries[0]
	for _, e := range entries[1:] {
		v1, _ := ParseVersion(e.Descriptor.Version)
		v2, _ := ParseVersion(latest.Descriptor.Version)
		if v2.Less(v1) {
			latest = e
		}
	}
	if contains(latest.Descriptor.Backends, backend) {
		return latest
	}
	return entries[0]
}

func contains(slice []string, s string) bool {
	for _, item := range slice {
		if item == s {
			return true
		}
	}
	return false
}
