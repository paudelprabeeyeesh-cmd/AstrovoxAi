
from product_polish.experiment_manager import ExperimentManager


def test_create_and_get_experiment():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        name="button_color_test",
        variants=[
            {"id": "red", "name": "Red Button", "weight": 1.0},
            {"id": "blue", "name": "Blue Button", "weight": 1.0},
        ],
        status="running",
    )
    assert experiment.name == "button_color_test"
    assert experiment.status == "running"
    assert len(experiment.variants) == 2

    fetched = manager.get_experiment(experiment.id)
    assert fetched is not None
    assert fetched.id == experiment.id


def test_list_experiments_sorted_by_created_at():
    manager = ExperimentManager()
    manager.create_experiment("old", [{"id": "a", "name": "A"}])
    manager.create_experiment("new", [{"id": "b", "name": "B"}])
    experiments = manager.list_experiments()
    assert experiments[0].name == "new"
    assert experiments[1].name == "old"


def test_assign_variant_returns_none_for_draft():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        "paused", [{"id": "a", "name": "A"}], status="draft"
    )
    assert manager.assign_variant(experiment.id, "user_1") is None


def test_record_and_aggregate_results():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        "clicks",
        [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
        status="running",
    )
    manager.record_result(experiment.id, "a", "user_1", "clicks", 5.0)
    manager.record_result(experiment.id, "a", "user_2", "clicks", 3.0)
    manager.record_result(experiment.id, "b", "user_3", "clicks", 7.0)

    aggregated = manager.aggregate_results(experiment.id, "clicks")
    assert aggregated["a"]["count"] == 2
    assert abs(aggregated["a"]["mean"] - 4.0) < 1e-9
    assert aggregated["b"]["count"] == 1
    assert aggregated["b"]["min"] == 7.0
    assert aggregated["b"]["max"] == 7.0


def test_create_experiment_with_traffic_allocation():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        "traffic_test",
        [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
        traffic_allocation=0.5,
    )
    assert experiment.traffic_allocation == 0.5


def test_get_experiment_returns_none_for_missing():
    manager = ExperimentManager()
    assert manager.get_experiment("missing") is None


def test_assign_variant_for_missing_or_non_running():
    manager = ExperimentManager()
    experiment = manager.create_experiment("pause", [{"id": "a", "name": "A"}], status="paused")
    assert manager.assign_variant(experiment.id, "user_1") is None
    assert manager.assign_variant("missing", "user_1") is None


def test_assign_variant_returns_variant_id():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        "var_test",
        [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
        status="running",
    )
    assigned = manager.assign_variant(experiment.id, "user_1")
    assert assigned in ("a", "b")


def test_record_result_and_get_with_metric_filter():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        "metrics",
        [{"id": "a", "name": "A"}],
        status="running",
    )
    manager.record_result(experiment.id, "a", "u1", "clicks", 4.0)
    manager.record_result(experiment.id, "a", "u1", "clicks", 2.0)
    manager.record_result(experiment.id, "a", "u1", "views", 1.0)

    clicks = manager.get_results(experiment.id, metric="clicks")
    assert len(clicks) == 2
    views = manager.get_results(experiment.id, metric="views")
    assert len(views) == 1


def test_aggregate_results_returns_empty_for_no_results():
    manager = ExperimentManager()
    experiment = manager.create_experiment(
        "empty",
        [{"id": "a", "name": "A"}],
        status="running",
    )
    aggregated = manager.aggregate_results(experiment.id, "clicks")
    assert aggregated == {}
