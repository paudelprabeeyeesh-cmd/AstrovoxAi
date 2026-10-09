
from advanced_planning.plan_verification import (
    State,
    CTLFormula,
    KripkeModel,
    ModelChecker,
    PlanVerifier,
)


def _make_simple_kripke():
    km = KripkeModel()
    km.add_state("s0", State({"a": True}, 0))
    km.add_state("s1", State({"b": True}, 1))
    km.add_transition("s0", "s1")
    km.add_transition("s1", "s1")
    km.add_atomic_prop("s0", "a")
    km.add_atomic_prop("s1", "b")
    km.set_initial("s0")
    return km


class TestKripkeModel:

    def test_add_state(self):
        km = KripkeModel()
        km.add_state("s0", State({}))
        assert "s0" in km.states
        assert "s0" in km.transitions
        assert "s0" in km.atomic_props

    def test_add_transition(self):
        km = KripkeModel()
        km.add_state("s0", State({}))
        km.add_state("s1", State({}))
        km.add_transition("s0", "s1")
        assert "s1" in km.get_successors("s0")

    def test_get_successors_empty(self):
        km = KripkeModel()
        assert km.get_successors("nonexistent") == set()

    def test_add_atomic_prop(self):
        km = KripkeModel()
        km.add_state("s0", State({}))
        km.add_atomic_prop("s0", "ready")
        assert "ready" in km.atomic_props["s0"]

    def test_set_initial(self):
        km = KripkeModel()
        km.set_initial("s0")
        assert "s0" in km.initial_states


class TestModelChecker:

    def test_atom_true(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        assert mc.check(CTLFormula("atom", atom="a"), "s0") is True

    def test_atom_false(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        assert mc.check(CTLFormula("atom", atom="c"), "s0") is False

    def test_not_formula(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        assert mc.check(CTLFormula("not", [CTLFormula("atom", atom="a")]), "s0") is False
        assert mc.check(CTLFormula("not", [CTLFormula("atom", atom="c")]), "s0") is True

    def test_and_formula(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        f1 = CTLFormula("atom", atom="a")
        f2 = CTLFormula("atom", atom="b")
        assert mc.check(CTLFormula("and", [f1, f2]), "s0") is False
        assert mc.check(CTLFormula("and", [f1, f2]), "s1") is False

    def test_or_formula(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        f1 = CTLFormula("atom", atom="a")
        f2 = CTLFormula("atom", atom="c")
        assert mc.check(CTLFormula("or", [f1, f2]), "s0") is True
        assert mc.check(CTLFormula("or", [f1, f2]), "s1") is False

    def test_ex_formula(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        assert mc.check(CTLFormula("EX", [CTLFormula("atom", atom="b")]), "s0") is True
        assert mc.check(CTLFormula("EX", [CTLFormula("atom", atom="a")]), "s0") is False

    def test_eu_formula(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        phi = CTLFormula("atom", atom="a")
        psi = CTLFormula("atom", atom="b")
        assert mc.check(CTLFormula("EU", [phi, psi]), "s0") is True
        assert mc.check(CTLFormula("EU", [phi, psi]), "s1") is True

    def test_af_formula(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        assert mc.check(CTLFormula("AF", [CTLFormula("atom", atom="b")]), "s0") is False
        assert mc.check(CTLFormula("AF", [CTLFormula("atom", atom="b")]), "s1") is True

    def test_ag_formula(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        assert mc.check(CTLFormula("AG", [CTLFormula("atom", atom="b")]), "s0") is False
        assert mc.check(CTLFormula("AG", [CTLFormula("atom", atom="b")]), "s1") is True

    def test_check_all_initial(self):
        km = _make_simple_kripke()
        mc = ModelChecker(km)
        assert mc.check_all_initial(CTLFormula("atom", atom="a")) is True
        assert mc.check_all_initial(CTLFormula("atom", atom="b")) is False


class TestPlanVerifier:

    def test_verify_valid_plan(self):
        pv = PlanVerifier()
        result = pv.verify([1, 2, 3], lambda p: len(p) > 0)
        assert result["valid"] is True
        assert len(pv.verification_results) == 1

    def test_verify_invalid_plan(self):
        pv = PlanVerifier()
        result = pv.verify([], lambda p: len(p) > 0)
        assert result["valid"] is False

    def test_verify_checks_length(self):
        pv = PlanVerifier()
        result = pv.verify([], lambda p: True)
        assert result["checks"]["length"] is False
        assert result["checks"]["valid"] is True

    def test_simulate_tracks_trace(self):
        pv = PlanVerifier()
        state = {"x": 0}
        trace = pv.simulate(
            state, [1, 2, 3],
            lambda s, a: {"x": s["x"] + a},
            lambda s: s["x"] >= 5,
        )
        assert trace["goal_reached"] is True
        assert trace["trace_length"] == 4
        assert trace["final_state"]["x"] == 6

    def test_simulate_goal_not_reached(self):
        pv = PlanVerifier()
        trace = pv.simulate(
            {"x": 0}, [1],
            lambda s, a: {"x": s["x"] + a},
            lambda s: s["x"] >= 100,
        )
        assert trace["goal_reached"] is False
        assert trace["trace_length"] == 2

    def test_simulate_empty_plan(self):
        pv = PlanVerifier()
        trace = pv.simulate(
            {"x": 5}, [],
            lambda s, a: s,
            lambda s: s["x"] == 5,
        )
        assert trace["goal_reached"] is True
        assert trace["trace_length"] == 1
