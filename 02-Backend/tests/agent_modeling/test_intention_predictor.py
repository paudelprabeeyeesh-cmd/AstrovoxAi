from agent_modeling.intention_predictor import Action, IntentionHypothesis, IntentionPredictor


def test_record_action():
    predictor = IntentionPredictor()
    action = Action(action_type="move", target="kitchen", timestamp=1000.0, context={})
    predictor.record_action(action)
    assert len(predictor.actions) == 1
    assert predictor.actions[0].action_type == "move"


def test_predict_empty():
    predictor = IntentionPredictor()
    result = predictor.predict()
    assert result == []


def test_predict_returns_hypotheses():
    predictor = IntentionPredictor()
    predictor.record_action(Action("move", "kitchen", 1000.0))
    predictor.record_action(Action("move", "kitchen", 1001.0))
    predictor.record_action(Action("grab", "apple", 1002.0))
    result = predictor.predict(recent_actions=3)
    assert len(result) > 0
    assert all(isinstance(h, IntentionHypothesis) for h in result)


def test_top_hypotheses():
    predictor = IntentionPredictor()
    predictor.record_action(Action("move", "kitchen", 1000.0))
    predictor.record_action(Action("move", "kitchen", 1001.0))
    predictor.record_action(Action("grab", "apple", 1002.0))
    predictor.predict(recent_actions=3)
    top = predictor.top_hypotheses(k=1)
    assert len(top) == 1
    assert top[0].probability > 0.0


def test_intention_entropy_empty():
    predictor = IntentionPredictor()
    assert predictor.intention_entropy() == 0.0


def test_intention_entropy():
    predictor = IntentionPredictor()
    predictor.record_action(Action("move", "kitchen", 1000.0))
    predictor.record_action(Action("grab", "apple", 1001.0))
    predictor.predict(recent_actions=2)
    entropy = predictor.intention_entropy()
    assert entropy > 0.0


def test_update_hypothesis_evidence():
    predictor = IntentionPredictor()
    predictor.update_hypothesis_evidence("stealth", 0.8)
    assert "stealth" in predictor.hypotheses
    assert predictor.hypotheses["stealth"].probability > 0.0


def test_action_transitions():
    predictor = IntentionPredictor()
    predictor.record_action(Action("move", "kitchen", 1000.0))
    predictor.record_action(Action("grab", "apple", 1001.0))
    assert "move" in predictor.action_transitions
    assert "grab" in predictor.action_transitions["move"]
