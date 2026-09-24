import numpy as np
from online_meta_learning.task_sampler import TaskSampler, TaskSpec


class TestTaskSampler:
    def test_register_and_sample(self):
        ts = TaskSampler(base_input_dim=8, base_output_dim=4)
        ts.register_task('task_a', num_samples=16, noise_scale=0.5, seed=42)
        x, y = ts.sample('task_a')
        assert x.shape == (16, 8)
        assert y.shape == (16, 4)
        assert ts.task_stats['task_a']['sampled'] == 1

    def test_sample_missing_task_raises(self):
        ts = TaskSampler()
        try:
            ts.sample('missing')
            assert False
        except KeyError:
            pass

    def test_sample_batch(self):
        ts = TaskSampler()
        ts.register_task('t1', num_samples=8)
        ts.register_task('t2', num_samples=8)
        result = ts.sample_batch(['t1', 't2'], samples_per_task=10)
        assert 't1' in result
        assert 't2' in result
        assert result['t1'][0].shape == (10, 8)

    def test_sample_random(self):
        ts = TaskSampler()
        ts.register_task('t1')
        ts.register_task('t2')
        results = ts.sample_random(num_tasks=3)
        assert len(results) == 3
        for tid, x, y in results:
            assert tid in ('t1', 't2')
            assert x.shape[1] == 8
            assert y.shape[1] == 4

    def test_sample_random_no_tasks_raises(self):
        ts = TaskSampler()
        try:
            ts.sample_random()
            assert False
        except RuntimeError:
            pass

    def test_get_task_distribution(self):
        ts = TaskSampler()
        ts.register_task('t1')
        ts.register_task('t2')
        ts.sample('t1')
        ts.sample('t1')
        ts.sample('t2')
        dist = ts.get_task_distribution()
        assert np.isclose(dist['t1'], 2 / 3)
        assert np.isclose(dist['t2'], 1 / 3)

    def test_get_report(self):
        ts = TaskSampler()
        ts.register_task('t1')
        report = ts.get_report()
        assert 'num_registered' in report
        assert report['num_registered'] == 1
        assert 'task_ids' in report
