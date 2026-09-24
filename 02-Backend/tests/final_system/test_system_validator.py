from final_system.system_validator import Severity, SystemValidator, ValidationRule, ValidationResult


def test_valid_context():
    validator = SystemValidator()
    validator.add_rule(ValidationRule(name="positive", check=lambda ctx: ctx > 0))
    results = validator.validate(10)
    assert len(results) == 1
    assert results[0].passed is True


def test_invalid_context():
    validator = SystemValidator()
    validator.add_rule(ValidationRule(name="positive", check=lambda ctx: ctx > 0, severity=Severity.ERROR))
    results = validator.validate(-1)
    assert results[0].passed is False
    assert results[0].severity == Severity.ERROR


def test_is_valid_true():
    validator = SystemValidator()
    validator.add_rule(ValidationRule(name="ok", check=lambda ctx: True))
    assert validator.is_valid("anything") is True


def test_is_valid_false():
    validator = SystemValidator()
    validator.add_rule(ValidationRule(name="bad", check=lambda ctx: False, severity=Severity.ERROR))
    assert validator.is_valid("anything") is False


def test_remove_rule():
    validator = SystemValidator()
    validator.add_rule(ValidationRule(name="r", check=lambda ctx: True))
    validator.remove_rule("r")
    assert validator.validate(None) == []
