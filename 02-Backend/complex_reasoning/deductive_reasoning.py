from typing import List, Tuple, Optional, Dict, Set


class Literal:
    def __init__(self, name: str, negated: bool = False, value: Optional[float] = None):
        self.name = name
        self.negated = negated
        self.value = value

    def __neg__(self) -> "Literal":
        return Literal(self.name, negated=not self.negated, value=self.value)

    def __hash__(self):
        return hash((self.name, self.negated))

    def __eq__(self, other):
        return self.name == other.name and self.negated == other.negated

    def __repr__(self):
        return f"{'NOT ' if self.negated else ''}{self.name}"


class Clause:
    def __init__(self, literals: Optional[List[Literal]] = None):
        self.literals: List[Literal] = literals or []

    def add_literal(self, lit: Literal):
        self.literals.append(lit)

    def resolve(self, other: "Clause", lit_name: str) -> Optional["Clause"]:
        new_lits = []
        found_self = False
        found_other = False
        for lit in self.literals:
            if lit.name == lit_name and not found_self:
                found_self = True
            else:
                new_lits.append(lit)
        for lit in other.literals:
            if lit.name == lit_name and not found_other:
                found_other = True
            else:
                new_lits.append(lit)
        if not (found_self and found_other):
            return None
        unique = []
        seen = set()
        for lit in new_lits:
            key = hash(lit)
            if key not in seen:
                seen.add(key)
                unique.append(lit)
        return Clause(unique)

    def is_empty(self) -> bool:
        return len(self.literals) == 0

    def __repr__(self):
        return " OR ".join(map(str, self.literals)) if self.literals else "FALSE"


class KnowledgeBase:
    def __init__(self):
        self.clauses: List[Clause] = []
        self.facts: Dict[str, float] = {}
        self.rules: List[Tuple[Clause, Clause]] = []

    def add_clause(self, clause: Clause):
        self.clauses.append(clause)

    def add_fact(self, name: str, value: float = 1.0):
        self.facts[name] = value

    def add_rule(self, antecedents: Clause, consequent: Clause):
        self.rules.append((antecedents, consequent))

    def forward_chain(self) -> Set[str]:
        derived: Set[str] = set(self.facts.keys())
        changed = True
        while changed:
            changed = False
            for ants, cons in self.rules:
                if all(not lit.negated and lit.name in derived for lit in ants.literals):
                    for lit in cons.literals:
                        if not lit.negated and lit.name not in derived:
                            derived.add(lit.name)
                            changed = True
        return derived

    def backward_chain(self, goal: str) -> bool:
        proven: Set[str] = set()

        def prove(g: str) -> bool:
            if g in self.facts and self.facts[g] > 0.5:
                return True
            if g in proven:
                return True
            proven.add(g)
            for ants, cons in self.rules:
                for lit in cons.literals:
                    if lit.name == g and not lit.negated:
                        if all(prove(a.name) for a in ants.literals if not a.negated):
                            return True
            return False

        return prove(goal)

    def resolution(self, goal_clause: Clause, max_iterations: int = 1000) -> bool:
        new = list(self.clauses)
        new.extend([Clause([Literal(g)]) for g in self.facts])
        negations = [Clause([Literal(lit.negated and lit.name or lit.name, negated=not lit.negated)]) for c in [goal_clause] for lit in c.literals]
        new.extend(negations)
        for _ in range(max_iterations):
            resolvents = []
            n = len(new)
            found_empty = False
            for i in range(n):
                for j in range(i + 1, n):
                    for lit in new[i].literals:
                        resolved = new[i].resolve(new[j], lit.name)
                    if resolved is not None:
                        if resolved.is_empty():
                            found_empty = True
                            return True
                        resolvents.append(resolved)
            if not resolvents:
                return False
            unique = []
            seen = set()
            for c in resolvents:
                key = tuple(hash(lit) for lit in c.literals)
                if key not in seen:
                    seen.add(key)
                    unique.append(c)
            new = unique
            if found_empty:
                return True
        return False


class DeductiveEngine:
    def __init__(self):
        self.kb = KnowledgeBase()

    def add_premise(self, premise: str, value: float = 1.0):
        self.kb.add_fact(premise, value)

    def add_rule(self, antecedent_terms: List[str], consequent_term: str):
        ant_clause = Clause([Literal(t) for t in antecedent_terms])
        cons_clause = Clause([Literal(consequent_term)])
        self.kb.add_rule(ant_clause, cons_clause)

    def modus_ponens(self, antecedent: str, consequent: str) -> bool:
        if antecedent not in self.kb.facts or self.kb.facts[antecedent] <= 0.5:
            return False
        return self.kb.backward_chain(consequent)

    def syllogism(self, major: str, minor: str, middle: str) -> bool:
        self.add_rule([major], middle)
        self.add_rule([minor], middle)
        return self.kb.forward_chain() is not None

    def prove(self, goal: str) -> bool:
        return self.kb.backward_chain(goal)

    def theorem_prove(self, goal_clause: Clause) -> bool:
        return self.kb.resolution(goal_clause)
