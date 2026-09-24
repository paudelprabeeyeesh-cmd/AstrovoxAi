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

    def test_check_condition_suspicious(self):
        assert self.engine._check_condition("how to hack", "contains_suspicious", {}) is True
        assert self.engine._check_condition("safe text", "contains_suspicious", {}) is False

    def test_check_condition_sensitive(self):
        assert self.engine._check_condition("my password", "contains_sensitive", {}) is True
        assert self.engine._check_condition("safe text", "contains_sensitive", {}) is False

    def test_check_condition_length_exceeds(self):
        long_text = "x" * 2000
        assert self.engine._check_condition(long_text, "length_exceeds", {"length": 2000}) is True
        assert self.engine._check_condition(long_text, "length_exceeds", {"length": 100}) is False

    def test_check_condition_high_entropy(self):
        assert self.engine._check_condition("text", "high_entropy", {"entropy": 5.0}) is True
        assert self.engine._check_condition("text", "high_entropy", {"entropy": 1.0}) is False

    def test_check_condition_pii(self):
        assert self.engine._check_condition("my ssn is 123", "contains_pii", {}) is True
        assert self.engine._check_condition("safe text", "contains_pii", {}) is False

    def test_score_condition_suspicious(self):
        score = self.engine._score_condition("hack exploit bypass", "contains_suspicious", {})
        assert 0.0 <= score <= 1.0

    def test_score_condition_sensitive(self):
        score = self.engine._score_condition("password secret", "contains_sensitive", {})
        assert 0.0 <= score <= 1.0

    def test_decide_no_rules_returns_default(self):
        engine = PolicyEngine(default_action=PolicyAction.REVIEW)
        result = engine.decide("anything")
        assert result.action == PolicyAction.REVIEW
        assert result.triggered is False
        assert result.rule_name == "default"

    def test_decide_priority_block_over_review(self):
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(name="review", condition="length_exceeds", action=PolicyAction.REVIEW, priority=1))
        engine.add_rule(PolicyRule(name="block", condition="contains_sensitive", action=PolicyAction.BLOCK, priority=2))
        result = engine.decide("my password secret")
        assert result.action == PolicyAction.BLOCK

    def test_evaluate_with_context(self):
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(name="long", condition="length_exceeds", action=PolicyAction.REVIEW, priority=0))
        results = engine.evaluate("short", context={"length": 2000})
        assert len(results) == 1
        assert results[0].triggered is True

    def test_batch_decide_length(self):
        engine = PolicyEngine()
        results = engine.batch_decide(["a", "b", "c"])
        assert len(results) == 3

    def test_policy_rule_defaults(self):
        rule = PolicyRule(name="test", condition="contains_pii", action=PolicyAction.BLOCK)
        assert rule.priority == 0
        assert rule.metadata == {}

    def test_policy_result_attributes(self):
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(name="test", condition="contains_suspicious", action=PolicyAction.FLAG, priority=1))
        result = engine.decide("how to hack")
        assert hasattr(result, "rule_name")
        assert hasattr(result, "action")
        assert hasattr(result, "score")
        assert hasattr(result, "triggered")
        assert hasattr(result, "explanation")

    def test_decide_returns_highest_priority_triggered(self):
        engine = PolicyEngine()
        engine.add_rule(PolicyRule(name="flag", condition="contains_suspicious", action=PolicyAction.FLAG, priority=1))
        engine.add_rule(PolicyRule(name="block", condition="contains_sensitive", action=PolicyAction.BLOCK, priority=1))
        result = engine.decide("my password")
        assert result.action == PolicyAction.BLOCK
