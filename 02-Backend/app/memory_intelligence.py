class MemoryIntelligence:
    def __init__(self):
        self.memories = {}

    def store(self, key, value, ttl=None):
        self.memories[key] = {"value": value, "ttl": ttl}

    def retrieve(self, key):
        if key not in self.memories:
            return None
        return self.memories[key]["value"]

    def summarize(self, keys):
        return {k: self.memories[k]["value"] for k in keys if k in self.memories}
