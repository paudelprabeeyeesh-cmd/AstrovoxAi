import numpy as np
import pytest
from training_engine.pipeline_bubble import PipelineScheduler


def test_interleaved_schedule_length():
    ps = PipelineScheduler(num_stages=3, num_microbatches=4)
    schedule = ps.interleaved_schedule()
    assert len(schedule) == 3 * 4 * 2


def test_zero_bubble_schedule_length():
    ps = PipelineScheduler(num_stages=3, num_microbatches=4)
    schedule = ps.zero_bubble_schedule()
    assert len(schedule) > 0
    for mb, stage, typ in schedule:
        assert typ in ("forward", "backward")
        assert 0 <= stage < 3
        assert 0 <= mb < 4
