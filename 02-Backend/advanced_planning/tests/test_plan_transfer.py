
import pytest
from advanced_planning.plan_transfer import DomainMapping, PlanTransfer


def test_domain_mapping_creation():
    dm = DomainMapping("grid", "blocks")
    assert dm.source_domain == "grid"
    assert dm.target_domain == "blocks"


def test_domain_mapping_map_action():
    dm = DomainMapping("grid", "blocks")
    dm.map_action("move_north", "stack_block", confidence=0.9)
    assert dm.action_mapping["move_north"] == "stack_block"
    assert dm.transfer_score["move_north"] == 0.9


def test_domain_mapping_translate_plan():
    dm = DomainMapping("g1", "g2")
    dm.map_action("go", "fly")
    dm.map_action("pick", "grab")
    plan = ["go", "pick"]
    translated = dm.translate_plan(plan)
    assert translated == ["fly", "grab"]


def test_domain_mapping_unknown_action():
    dm = DomainMapping("g1", "g2")
    translated = dm.translate_plan(["unknown"])
    assert translated == ["unknown"]


def test_domain_mapping_similarity():
    dm = DomainMapping("g1", "g2")
    s1 = {"x": 1, "y": 2, "z": 3}
    s2 = {"x": 1, "y": 5, "z": 3}
    sim = dm.similarity(s1, s2)
    assert 0.0 <= sim <= 1.0
    assert sim == pytest.approx(2 / 3, abs=0.01)


def test_domain_mapping_similarity_no_overlap():
    dm = DomainMapping("g1", "g2")
    sim = dm.similarity({"a": 1}, {"b": 2})
    assert sim == 0.0


def test_plan_transfer_register():
    pt = PlanTransfer()
    dm = DomainMapping("source", "target")
    dm.map_action("a", "A")
    pt.register_mapping(dm)
    assert len(pt.domain_mappings) == 1


def test_plan_transfer_translate():
    pt = PlanTransfer()
    dm = DomainMapping("d1", "d2")
    dm.map_action("walk", "fly", confidence=0.8)
    pt.register_mapping(dm)
    plan, confidence = pt.transfer(["walk"], "d1", "d2")
    assert plan == ["fly"]
    assert confidence == pytest.approx(0.8)


def test_plan_transfer_no_mapping():
    pt = PlanTransfer()
    plan, confidence = pt.transfer(["walk"], "unknown", "target")
    assert plan == ["walk"]
    assert confidence == 0.0


def test_plan_transfer_adapt():
    pt = PlanTransfer()
    dm = DomainMapping("d1", "d2")
    dm.map_action("go", "move")
    pt.register_mapping(dm)
    plan, _ = pt.transfer(["go"], "d1", "d2")
    adapted = pt.adapt_plan(plan, {"speed": "fast"}, lambda a, ctx: f"{a}_fast")
    assert adapted == ["move_fast"]


def test_plan_transfer_quality():
    pt = PlanTransfer()
    dm = DomainMapping("d1", "d2")
    dm.map_action("a", "A", confidence=0.8)
    dm.map_action("b", "B", confidence=0.9)
    quality = pt.evaluate_transfer_quality(["a", "b"], ["A", "B"], dm)
    assert quality == pytest.approx(0.85, abs=0.01)


def test_plan_transfer_history():
    pt = PlanTransfer()
    dm = DomainMapping("d1", "d2")
    dm.map_action("a", "A")
    pt.register_mapping(dm)
    pt.transfer(["a"], "d1", "d2")
    assert len(pt.transfer_history) == 1
