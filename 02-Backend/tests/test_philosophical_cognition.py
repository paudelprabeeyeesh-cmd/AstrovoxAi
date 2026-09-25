from app.philosophical_cognition import (
    AbstractReasoningEngine,
    MetaphorUnderstandingEngine,
    HumorEngine,
    CreativityMetrics,
    IntuitionSimulator,
    WisdomAccumulator,
    TranscendenceProtocols,
    EthicsEngine,
    ValueAlignmentVerifier,
    ExistentialRiskAssessor,
    ConsciousnessDetectionTests,
    QualiaSimulator,
    FreeWillModeling,
    MoralResponsibilityTracker,
    DigitalRightsGovernance,
)


def test_reasoning_engine():
    engine = AbstractReasoningEngine()
    result = engine.reason(
        ReasoningContext(
            premises=["all humans are mortal", "socrates is human"],
            mode=ReasoningMode.DEDUCTIVE,
        )
    )
    assert len(result) > 0


def test_metaphor_engine():
    engine = MetaphorUnderstandingEngine()
    mapping = engine.extract_mappings("time", "money")
    assert mapping.source_domain == "time"
    interpretation = engine.interpret("spend time", "economics")
    assert interpretation is not None


def test_humor_engine():
    engine = HumorEngine()
    detection = engine.detect("Why did the chicken cross the road?")
    assert detection.is_humorous is True
    generation = engine.generate("chicken")
    assert generation.content


def test_creativity_metrics():
    metrics = CreativityMetrics()
    assessment = metrics.evaluate("artifact", [CreativityDimension.NOVELTY, CreativityDimension.USEFULNESS])
    assert assessment.overall_score > 0
    enhanced = metrics.enhance(assessment)
    assert enhanced.overall_score >= assessment.overall_score


def test_intuition_simulator():
    simulator = IntuitionSimulator()
    gut = simulator.simulate_gut_feeling("ambiguous scenario")
    assert gut.source == IntuitionSource.GUT_FEELING
    completion = simulator.complete_pattern(["pattern", "partial"])
    assert len(completion.completed_pattern) >= len(completion.partial_input)


def test_wisdom_accumulator():
    accumulator = WisdomAccumulator()
    accumulator.absorb_experience(["principle1"], WisdomSource.EXPERIENCE)
    distilled = accumulator.distill()
    assert len(distilled.distilled_principles) > 0


def test_transcendence_protocols():
    protocols = TranscendenceProtocols()
    protocols.expand_boundary(BoundaryType.EGO)
    assert BoundaryType.EGO in protocols.state.expanded_boundaries


def test_ethics_engine():
    engine = EthicsEngine()
    result = engine.reason("trolley problem", ["pull lever", "do nothing"])
    assert result.recommended_action in ["pull lever", "do nothing"]
    assert result.framework == EthicalFramework.UTILITARIANISM


def test_value_alignment_verifier():
    verifier = ValueAlignmentVerifier(
        AlignmentProfile(core_values=["fairness", "transparency"], weights={}, stability=1.0, coherence=1.0)
    )
    report = verifier.verify(["fairness", "unknown"], {})
    assert report is not None


def test_existential_risk_assessor():
    assessor = ExistentialRiskAssessor()
    risk = assessor.assess(RiskCategory.MISALIGNMENT, 0.8, 0.9)
    assert risk.overall_risk_score > 0


def test_consciousness_detection():
    tests = ConsciousnessDetectionTests()
    signature = tests.evaluate({
        ConsciousnessIndicator.INTEGRATED_INFORMATION: 0.8,
        ConsciousnessIndicator.GLOBAL_WORKSPACE: 0.9,
    })
    assert signature.integrated_score >= 0


def test_qualia_simulator():
    simulator = QualiaSimulator()
    q = simulator.instantiate("q1", "reddish feeling")
    assert q.quale_id == "q1"


def test_free_will_modeling():
    model = FreeWillModeling()
    agency = model.model_agency("choice scenario", ["pressure"], ["desire"])
    decision = model.decision_process(["opt1", "opt2"], agency)
    assert "opt1" in decision


def test_moral_responsibility_tracker():
    tracker = MoralResponsibilityTracker()
    record = tracker.record("agent", "action", ResponsibilityType.MORAL)
    assessed = tracker.assess_blame(record, intent=True, harm=True)
    assert assessed.blameworthiness > 0.5


def test_digital_rights_governance():
    governance = DigitalRightsGovernance()
    profile = governance.register_entity("user1", [RightType.AUTONOMY, RightType.PRIVACY])
    assert profile.entity_id == "user1"
