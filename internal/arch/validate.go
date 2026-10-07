package arch

import "sort"

// Rule constrains the imports of packages whose path matches From.
// Deny prefixes are always rejected; when Allow is non-empty, imports
// must match at least one Allow prefix.
type Rule struct {
	From  string
	Allow []string
	Deny  []string
}

// ValidateDependencies checks the graph against the given rules and
// returns all violations sorted by source then target package.
func ValidateDependencies(g *DependencyGraph, rules []Rule) []Violation {
	var violations []Violation
	for from, edges := range g.edges {
		rule := matchingRule(rules, from)
		if rule == nil {
			continue
		}
		for to := range edges {
			if matchesAny(to, rule.Deny) {
				violations = append(violations, Violation{
					From:    from,
					To:      to,
					Rule:    "deny",
					Message: from + " must not import denied package " + to,
				})
				continue
			}
			if len(rule.Allow) > 0 && !matchesAny(to, rule.Allow) {
				violations = append(violations, Violation{
					From:    from,
					To:      to,
					Rule:    "allow",
					Message: from + " may not import " + to + " (not in allow list)",
				})
			}
		}
	}

	sort.Slice(violations, func(i, j int) bool {
		if violations[i].From != violations[j].From {
			return violations[i].From < violations[j].From
		}
		return violations[i].To < violations[j].To
	})
	return violations
}

func matchingRule(rules []Rule, path string) *Rule {
	best := -1
	bestLen := -1
	for i := range rules {
		if len(rules[i].From) > bestLen && (path == rules[i].From || len(path) > len(rules[i].From) && path[:len(rules[i].From)] == rules[i].From) {
			best = i
			bestLen = len(rules[i].From)
		}
	}
	if best < 0 {
		return nil
	}
	return &rules[best]
}

func matchesAny(path string, prefixes []string) bool {
	for _, prefix := range prefixes {
		if path == prefix || len(path) > len(prefix) && path[:len(prefix)] == prefix {
			return true
		}
	}
	return false
}
