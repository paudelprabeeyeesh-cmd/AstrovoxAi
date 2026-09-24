import numpy as np


class PipelineScheduler:
    def __init__(self, num_stages, num_microbatches):
        self.num_stages = int(num_stages)
        self.num_microbatches = int(num_microbatches)

    def interleaved_schedule(self):
        schedule = []
        for mb in range(self.num_microbatches):
            for stage in range(self.num_stages):
                schedule.append((mb, stage, "forward"))
            for stage in reversed(range(self.num_stages)):
                schedule.append((mb, stage, "backward"))
        return schedule

    def zero_bubble_schedule(self):
        schedule = []
        bubble = self.num_stages - 1
        for t in range(self.num_microbatches + bubble):
            for stage in range(self.num_stages):
                mb = t - stage
                if 0 <= mb < self.num_microbatches:
                    schedule.append((mb, stage, "forward"))
            for stage in reversed(range(self.num_stages)):
                mb = t - stage
                if 0 <= mb < self.num_microbatches:
                    schedule.append((mb, stage, "backward"))
        return schedule
