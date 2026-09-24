import numpy as np


def all_reduce(data, world_size):
    return sum(data) / world_size


def all_gather(shard, world_size):
    return [shard] * world_size


class DataParallel:
    def __init__(self, world_size):
        self.world_size = int(world_size)

    def step(self, replicas):
        reduced = all_reduce(replicas, self.world_size)
        return [reduced] * self.world_size


class TensorParallel:
    def __init__(self, world_size):
        self.world_size = int(world_size)

    def gather(self, shard):
        return all_gather(shard, self.world_size)


class PipelineParallel:
    def __init__(self, num_stages, num_microbatches):
        self.num_stages = int(num_stages)
        self.num_microbatches = int(num_microbatches)

    def schedule_1f1b(self):
        schedule = []
        for mb in range(self.num_microbatches):
            for stage in range(self.num_stages):
                schedule.append((mb, stage, "forward"))
            for stage in range(self.num_stages):
                schedule.append((mb, stage, "backward"))
        return schedule
