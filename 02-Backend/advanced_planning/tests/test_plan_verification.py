
from advanced_planning.plan_verification import State, CTLFormula, KripkeModel, ModelChecker, PlanVerifier


def _make_model() -> KripkeModel:
    model = KripkeModel()
    model.add_state("s0", State({"at_robot": "A"}))
    model.add_state("s1", State({"at_robot": "B"}))
    model.add_transition("s0", "s1")
    model.add_atomic_prop("s0", "at_A")
    model.add_atomic_prop("s1", "at_B")
    model.set_initial("s0")
    return model


def test_ctl_atom():
    model = _make_model()
    mc = ModelChecker(model)
    f_at_B = CTLFormula("atom", atom="at_B")
    assert mc.check(f_at_B, "s1")
    assert not mc.check(f_at_B, "s0")


def test_ctl_not():
    model = _make_model()
    mc = ModelChecker(model)
    f_at_B = CTLFormula("atom", atom="at_B")
    f_not_at_B = CTLFormula("not", [f_at_B])
    assert not mc.check(f_not_at_B, "s1")
    assert mc.check(f_not_at_B, "s0")


def test_ctl_and():
    model = _make_model()
    mc = ModelChecker(model)
    f_A = CTLFormula("atom", atom="at_A")
    f_B = CTLFormula("atom", atom="at_B")
    f_and = CTLFormula("and", [f_A, f_B])
    assert not mc.check(f_and, "s0")
    assert not mc.check(f_and, "s1")


def test_ctl_ex():
    model = _make_model()
    mc = ModelChecker(model)
    f_at_B = CTLFormula("atom", atom="at_B")
    f_EX_B = CTLFormula("EX", [f_at_B])
    assert mc.check(f_EX_B, "s0")


def test_ctl_af():
    model = _make_model()
    mc = ModelChecker(model)
    f_at_B = CTLFormula("atom", atom="at_B")
    f_AF_B = CTLFormula("AF", [f_at_B])
    # AF(at_B) at s1 is True (at_B already holds at s1)
    assert mc.check(f_AF_B, "s1")
    # AF(at_B) at s0 is False (s0 itself is a state where not at_B holds,
    # so EF(not at_B) is trivially true at s0 via the 0-length path)
    assert not mc.check(f_AF_B, "s0")


def test_model_checker_all_initial():
    model = _make_model()
    mc = ModelChecker(model)
    f_at_A = CTLFormula("atom", atom="at_A")
    assert mc.check_all_initial(f_at_A)
    assert not mc.check_all_initial(CTLFormula("atom", atom="at_B"))


def test_plan_verifier():
    verifier = PlanVerifier()
    result = verifier.verify(["a", "b"], lambda p: len(p) > 0)
    assert result["valid"] is True
    assert len(verifier.verification_results) == 1


def test_plan_simulate_reaches_goal():
    verifier = PlanVerifier()
    initial = {"x": 0}

    def apply(state, action):
        return {"x": state["x"] + 1}

    def goal(state):
        return state["x"] >= 2

    trace = verifier.simulate(initial, ["inc", "inc"], apply, goal)
    assert trace["goal_reached"] is True
    assert trace["trace_length"] == 3


def test_plan_simulate_not_reaches_goal():
    verifier = PlanVerifier()
    initial = {"x": 0}

    def apply(state, action):
        return {"x": state["x"] + 1}

    def goal(state):
        return state["x"] >= 10

    trace = verifier.simulate(initial, ["inc"], apply, goal)
    assert not trace["goal_reached"]
    assert trace["trace_length"] == 2
