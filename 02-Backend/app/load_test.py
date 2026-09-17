class LoadTestSuite:
    def __init__(self):
        self.scenarios = {}

    def add_scenario(self, name, config):
        self.scenarios[name] = config

    def run(self, name, duration):
        if name not in self.scenarios:
            raise ValueError(f"Scenario {name} not found")
        return self.scenarios[name].execute(duration)

    def aggregate_results(self, scenario_names):
        return {name: self.scenarios[name].results() for name in scenario_names}
