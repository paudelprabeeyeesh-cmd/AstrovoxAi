from agent_modeling.belief_tracker import Belief, BeliefState, BeliefTracker


def test_observe_creates_belief():
    tracker = BeliefTracker()
    belief = tracker.observe("proposition_1", 0.8, "source_a", 1000.0)
    assert belief.proposition == "proposition_1"
    assert belief.confidence > 0.0
    assert belief.evidence_count == 1


def test_observe_updates_existing_belief():
    tracker = BeliefTracker()
    tracker.observe("proposition_1", 0.5, "source_a", 1000.0)
    tracker.observe("proposition_1", 0.9, "source_b", 1001.0)
    belief = tracker.beliefs["proposition_1"]
    assert belief.evidence_count == 2
    assert belief.confidence > 0.0


def test_get_belief_state_empty():
    tracker = BeliefTracker()
    state = tracker.get_belief_state()
    assert state.entropy == 0.0
    assert state.confidence_summary == {}


def test_get_belief_state_populated():
    tracker = BeliefTracker()
    tracker.observe("p1", 0.9, "s1", 1000.0)
    tracker.observe("p2", 0.3, "s2", 1001.0)
    state = tracker.get_belief_state()
    assert "p1" in state.beliefs
    assert "p2" in state.beliefs
    assert state.entropy > 0.0
    assert "p1" in state.confidence_summary


def test_most_confident():
    tracker = BeliefTracker()
    tracker.observe("low", 0.2, "s", 1000.0)
    tracker.observe("high", 0.9, "s", 1001.0)
    top = tracker.most_confident(top_k=1)
    assert top[0].proposition == "high"


def test_least_confident():
    tracker = BeliefTracker()
    tracker.observe("low", 0.2, "s", 1000.0)
    tracker.observe("high", 0.9, "s", 1001.0)
    bottom = tracker.least_confident(top_k=1)
    assert bottom[0].proposition == "low"


def test_conflicting_beliefs():
    tracker = BeliefTracker()
    for _ in range(3):
        tracker.observe("p1", 0.5, "s1", 1000.0)
    for _ in range(3):
        tracker.observe("p2", 0.5, "s2", 1001.0)
    conflicts = tracker.conflicting_beliefs(threshold=0.3)
    assert len(conflicts) > 0


def test_conflicting_beliefs_no_conflicts():
    tracker = BeliefTracker()
    tracker.observe("p1", 0.1, "s", 1000.0)
    tracker.observe("p2", 0.9, "s", 1001.0)
    conflicts = tracker.conflicting_beliefs(threshold=0.3)
    assert len(conflicts) == 0


def test_confidence_bounds():
    tracker = BeliefTracker()
    b1 = tracker.observe("p1", -0.5, "s", 1000.0)
    b2 = tracker.observe("p2", 1.5, "s", 1001.0)
    assert 0.0 <= b1.confidence <= 1.0
    assert 0.0 <= b2.confidence <= 1.0
