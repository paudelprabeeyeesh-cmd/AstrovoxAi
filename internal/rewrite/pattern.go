package rewrite

// PatternLibrary stores reusable patterns.
type PatternLibrary struct {
	patterns map[string]*Pattern
}

// NewPatternLibrary creates a new library.
func NewPatternLibrary() *PatternLibrary {
	return &PatternLibrary{patterns: make(map[string]*Pattern)}
}

// Register adds a named pattern.
func (l *PatternLibrary) Register(name string, p *Pattern) {
	l.patterns[name] = p
}

// Get retrieves a pattern by name.
func (l *PatternLibrary) Get(name string) *Pattern {
	return l.patterns[name]
}

// List returns all registered pattern names.
func (l *PatternLibrary) List() []string {
	names := make([]string, 0, len(l.patterns))
	for name := range l.patterns {
		names = append(names, name)
	}
	return names
}
