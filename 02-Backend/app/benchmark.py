class BenchmarkPlatform:
    def __init__(self):
        self.benchmarks = {}

    def register(self, name, runner):
        self.benchmarks[name] = runner

    def run(self, name, iterations=1):
        if name not in self.benchmarks:
            raise ValueError(f"Benchmark {name} not found")
        results = []
        for _ in range(iterations):
            results.append(self.benchmarks[name].execute())
        return results

    def compare(self, benchmark_names):
        comparison = {}
        for name in benchmark_names:
            comparison[name] = self.benchmarks[name].results()
        return comparison
