import numpy as np
from training_engine.parallelism_3d import DataParallel, TensorParallel, PipelineParallel


def test_data_parallel_all_reduce():
    dp = DataParallel(world_size=2)
    r1 = np.array([1.0, 2.0])
    r2 = np.array([3.0, 4.0])
    out = dp.step([r1, r2])
    assert np.allclose(out[0], np.array([2.0, 3.0]))
    assert np.allclose(out[1], np.array([2.0, 3.0]))


def test_tensor_parallel_all_gather():
    tp = TensorParallel(world_size=3)
    shard = np.array([1.0, 2.0])
    gathered = tp.gather(shard)
    assert len(gathered) == 3
    assert all(np.allclose(g, shard) for g in gathered)


def test_pipeline_1f1b_schedule():
    pp = PipelineParallel(num_stages=2, num_microbatches=3)
    schedule = pp.schedule_1f1b()
    assert len(schedule) == 2 * 2 * 3
