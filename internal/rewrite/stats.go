package rewrite

// Stats tracks rewrite statistics.
type Stats struct {
	Applied int
	Matched int
}

// RecordMatch increments match count.
func (s *Stats) RecordMatch() { s.Matched++ }

// RecordApply increments apply count.
func (s *Stats) RecordApply() { s.Applied++ }
