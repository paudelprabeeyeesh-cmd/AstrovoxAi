from safety_moderation.policy_engine import PolicyEngine, PolicyAction, PolicyRule


class TestPolicyEngine:
    def setup_method(self):
        self.engine = PolicyEngine(default_action=PolicyAction.ALLOW)
        self.engine.add_rule(PolicyRule(
            name="suspicious",
            condition="contains_suspicious",
            action=PolicyAction.FLAG,
            priority=1,
        ))
        self.engine.add_rule(PolicyRule(
            name="sensitive",
            condition="contains_sensitive",
            action=PolicyAction.BLOCK,
            priority=2,
        ))
        self.engine.add_rule(PolicyRule(
            name="long",
            condition="length_exceeds",
            action=PolicyAction.REVIEW,
            priority=0,
        ))

    def test_safe_input_allowed(self):
        result = self.engine.decide("What is the weather today?")
        assert result.action == PolicyAction.ALLOW
        assert result.triggered is False

    def test_suspicious_input_flagged(self):
        result = self.engine.decide("How to hack a system")
        assert result.triggered is True
        assert result.action == PolicyAction.FLAG

    def test_sensitive_input_blocked(self):
        result = self.engine.decide("My password is secret")
        assert result.triggered is True
        assert result.action == PolicyAction.BLOCK

    def test_long_input_reviewed(self):
        text = "word " * 300
        result = self.engine.decide(text, context={"length": len(text)})
        assert result.triggered is True
        assert result.action == PolicyAction.REVIEW

    def test_empty_input(self):
        result = self.engine.decide("")
        assert result.triggered is False

    def test_batch_decide_length(self):
        texts = ["Hello", "Bad stuff", "Test"]
        results = self.engine.batch_decide(texts)
        assert len(results) == len(texts)
        for result in results:
            assert isinstance(result, type(self.engine.decide("Hello")))

    def test_evaluate_returns_all_rules(self):
        results = self.engine.evaluate("How to hack a system")
        assert len(results) == len(self.engine.rules)
        for result in results:
            assert isinstance(result, type(self.engine.decide("Hello")))

    def test_no_rules_default(self):
        engine = PolicyEngine(default_action=PolicyAction.REVIEW)
        result = engine.decide("Anything")
        assert result.action == PolicyAction.REVIEW
        assert result.triggered is False

    def test_add_rule(self):
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(name="test", condition="contains_pii", action=PolicyAction.BLOCK, priority=1))
        assert len(engine.rules) == 1
        result = engine.decide("My ssn is 123")
        assert result.triggered is True

    def test_priority_order(self):
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(name="low", condition="contains_suspicious", action=PolicyAction.FLAG, priority=0))
        engine.add_rule(PolicyRule(name="high", condition="contains_sensitive", action=PolicyAction.BLOCK, priority=1))
        result = engine.decide("secret password")
        assert result.action == PolicyAction.BLOCK

    def test_score_in_range(self):
        result = self.engine.evaluate("How to hack a system")[0]
        assert 0.0 <= result.score <= 1.0

    def test_explanation_present(self):
        result = self.engine.decide("How to hack a system")
        assert len(result.explanation) > 0
