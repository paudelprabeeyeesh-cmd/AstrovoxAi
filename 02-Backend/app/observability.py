class ObservabilityPlatform:
    def __init__(self):
        self.metrics = {}
        self.traces = []

    def record_metric(self, name, value, tags=None):
        self.metrics[name] = {"value": value, "tags": tags or {}}

    def start_trace(self, operation):
        return {"operation": operation, "start": 0}

    def export(self):
        return {"metrics": self.metrics, "traces": self.traces}
