import numpy as np


class StragglerHandler:
    def __init__(self):
        self.step_times = {}

    def record_step(self, gpu_id, duration):
        if gpu_id not in self.step_times:
            self.step_times[gpu_id] = []
        self.step_times[gpu_id].append(duration)

    def detect(self):
        stragglers = []
        for gpu_id, times in self.step_times.items():
            if len(times) < 10:
                continue
            mean_time = np.mean(times)
            std_time = np.std(times)
            if std_time == 0:
                continue
            recent = times[-1]
            z = (recent - mean_time) / std_time
            if z > 3.0:
                stragglers.append(gpu_id)
        return stragglers

    def isolate(self, gpu_id):
        return {"gpu_id": gpu_id, "action": "isolated"}
