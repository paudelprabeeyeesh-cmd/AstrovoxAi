"""
Tests for product_polish.experiment_manager

Uses only stdlib.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from product_polish.experiment_manager import (  # noqa: E402
    Experiment,
    ExperimentManager,
    ExperimentResult,
    ExperimentVariant,
)


@pytest.fixture()
def manager():
    return ExperimentManager()


class TestExperimentVariant:
    def test_defaults(self):
        v = ExperimentVariant(id="v1", name="Control")
        assert v.id == "v1"
        assert v.name == "Control"
        assert v.weight == 1.0
        assert v.config == {}

    def test_custom_weight(self):
        v = ExperimentVariant(id="v2", name="Treatment", weight=0.3)
        assert v.weight == 0.3

    def test_to_dict(self):
        v = ExperimentVariant(id="v1", name="A", config={"color": "red"})
        d = v.to_dict()
        assert d["id"] == "v1"
        assert d["name"] == "A"
        assert d["config"]["color"] == "red"


class TestExperimentDataclass:
    def test_defaults(self):
        e = Experiment(id="exp1", name="Test", variants=[])
        assert e.status == "draft"
        assert e.traffic_allocation == 1.0
        assert e.created_at != ""
        assert "T" in e.created_at

    def test_custom_status(self):
        e = Experiment(id="exp2", name="Test2", variants=[], status="running")
        assert e.status == "running"

    def test_to_dict(self):
        v = ExperimentVariant(id="v1", name="A")
        e = Experiment(id="exp1", name="Test", variants=[v])
        d = e.to_dict()
        assert d["name"] == "Test"
        assert len(d["variants"]) == 1


class TestExperimentManagerCreate:
    def test_create_returns_experiment(self, manager):
        e = manager.create_experiment("ab_test", [{"id": "v1", "name": "A"}, {"id": "v2", "name": "B"}])
        assert isinstance(e, Experiment)

    def test_create_has_id(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}])
        assert e.id != ""

    def test_create_has_status_running(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}], status="running")
        assert e.status == "running"

    def test_create_stores_variants(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}, {"id": "v2", "name": "B"}])
        assert len(e.variants) == 2

    def test_create_returns_same_id_on_lookup(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}])
        got = manager.get_experiment(e.id)
        assert got is not None
        assert got.id == e.id


class TestExperimentManagerGet:
    def test_get_missing_returns_none(self, manager):
        assert manager.get_experiment("nonexistent") is None


class TestExperimentManagerList:
    def test_list_empty(self, manager):
        assert manager.list_experiments() == []

    def test_list_after_create(self, manager):
        manager.create_experiment("a", [{"id": "v1", "name": "A"}])
        assert len(manager.list_experiments()) == 1


class TestExperimentManagerAssignVariant:
    def test_assign_returns_variant_id(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}, {"id": "v2", "name": "B"}], status="running")
        variant = manager.assign_variant(e.id, "user_1")
        assert variant in {"v1", "v2"}

    def test_assign_none_for_draft(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}], status="draft")
        assert manager.assign_variant(e.id, "user_1") is None

    def test_assign_none_for_missing_experiment(self, manager):
        assert manager.assign_variant("missing", "user_1") is None

    def test_assign_deterministic_for_same_subject(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}, {"id": "v2", "name": "B"}], status="running")
        r1 = manager.assign_variant(e.id, "user_42")
        r2 = manager.assign_variant(e.id, "user_42")
        assert r1 == r2


class TestExperimentManagerRecordResult:
    def test_record_result_returns_result(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}], status="running")
        r = manager.record_result(e.id, "v1", "user_1", "conversion", 1.0)
        assert isinstance(r, ExperimentResult)
        assert r.experiment_id == e.id
        assert r.variant_id == "v1"
        assert r.metric == "conversion"

    def test_record_result_has_timestamp(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}], status="running")
        r = manager.record_result(e.id, "v1", "user_1", "revenue", 10.0)
        assert "T" in r.recorded_at


class TestExperimentManagerAggregateResults:
    def test_aggregate_returns_mean(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}], status="running")
        manager.record_result(e.id, "v1", "u1", "score", 10.0)
        manager.record_result(e.id, "v1", "u2", "score", 20.0)
        agg = manager.aggregate_results(e.id, "score")
        assert agg["v1"]["mean"] == 15.0
        assert agg["v1"]["count"] == 2

    def test_aggregate_empty_for_no_results(self, manager):
        e = manager.create_experiment("exp", [{"id": "v1", "name": "A"}], status="running")
        agg = manager.aggregate_results(e.id, "score")
        assert agg == {}
