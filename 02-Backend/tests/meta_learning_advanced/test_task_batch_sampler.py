from meta_learning_advanced.task_batch_sampler import TaskBatchSampler, TaskSpec


def test_task_spec_creation():
    spec = TaskSpec(task_id=1, input_dim=4, output_dim=3, num_support=10, num_query=5)
    assert spec.task_id == 1
    assert spec.input_dim == 4
    assert spec.output_dim == 3
    assert spec.metadata == {}


def test_task_spec_with_metadata():
    spec = TaskSpec(task_id=2, input_dim=8, output_dim=2, num_support=5, num_query=5, metadata={"domain": "vision"})
    assert spec.metadata["domain"] == "vision"


def test_sampler_initialization():
    sampler = TaskBatchSampler()
    assert sampler.task_specs == []
    assert sampler.history == []


def test_add_task_source():
    sampler = TaskBatchSampler()
    spec = TaskSpec(task_id=1, input_dim=4, output_dim=3, num_support=10, num_query=5)
    sampler.add_task_source(spec)
    assert len(sampler.task_specs) == 1


def test_sample_batch_without_replacement():
    specs = [TaskSpec(task_id=i, input_dim=4, output_dim=3, num_support=10, num_query=5) for i in range(5)]
    sampler = TaskBatchSampler(task_specs=specs, seed=42)
    batch = sampler.sample_batch(3, replacement=False)
    assert len(batch) == 3
    assert all(isinstance(s, TaskSpec) for s in batch)
    assert len(sampler.history) == 3


def test_sample_batch_with_replacement():
    specs = [TaskSpec(task_id=i, input_dim=4, output_dim=3, num_support=10, num_query=5) for i in range(3)]
    sampler = TaskBatchSampler(task_specs=specs, seed=42)
    batch = sampler.sample_batch(5, replacement=True)
    assert len(batch) == 5


def test_sample_batch_raises_when_empty():
    sampler = TaskBatchSampler()
    try:
        sampler.sample_batch(1)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_sample_stratified():
    specs = [
        TaskSpec(task_id=0, input_dim=4, output_dim=2, num_support=10, num_query=5, metadata={"group": "A"}),
        TaskSpec(task_id=1, input_dim=4, output_dim=2, num_support=10, num_query=5, metadata={"group": "A"}),
        TaskSpec(task_id=2, input_dim=4, output_dim=2, num_support=10, num_query=5, metadata={"group": "B"}),
        TaskSpec(task_id=3, input_dim=4, output_dim=2, num_support=10, num_query=5, metadata={"group": "B"}),
    ]
    sampler = TaskBatchSampler(task_specs=specs, seed=42)
    batch = sampler.sample_stratified(4, strata_key="group")
    assert len(batch) >= 2
    groups = {s.metadata["group"] for s in batch}
    assert len(groups) >= 1


def test_generate_task_data():
    spec = TaskSpec(task_id=1, input_dim=4, output_dim=3, num_support=10, num_query=5)
    sampler = TaskBatchSampler(seed=42)
    x_s, y_s, x_q, y_q = sampler.generate_task_data(spec)
    assert len(x_s) == 10
    assert all(len(row) == 4 for row in x_s)
    assert len(y_s) == 10
    assert len(x_q) == 5
    assert all(len(row) == 4 for row in x_q)
    assert len(y_q) == 5
    assert all(v in {0, 1, 2} for v in y_s)
    assert all(v in {0, 1, 2} for v in y_q)


def test_history_accumulation():
    specs = [TaskSpec(task_id=i, input_dim=4, output_dim=3, num_support=10, num_query=5) for i in range(3)]
    sampler = TaskBatchSampler(task_specs=specs, seed=42)
    sampler.sample_batch(2)
    sampler.sample_batch(2)
    assert len(sampler.history) == 4
    assert len(sampler.get_history()) == 4
