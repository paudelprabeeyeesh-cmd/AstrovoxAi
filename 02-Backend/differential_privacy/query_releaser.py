class QueryReleaser:
    def __init__(self, mechanism):
        self.mechanism = mechanism

    def release(self, query_func, *args, **kwargs):
        result = query_func(*args, **kwargs)
        if isinstance(result, (int, float)):
            return self.mechanism.release(result)
        return [self.mechanism.release(r) for r in result]
