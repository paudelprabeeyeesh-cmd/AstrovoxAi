class EvaluationLab:
    def __init__(self):
        self.experiments = {}

    def create_experiment(self, name, config):
        self.experiments[name] = config

    def run(self, name, dataset):
        if name not in self.experiments:
            raise ValueError(f"Experiment {name} not found")
        return self.experiments[name].evaluate(dataset)

    def compare(self, experiment_names):
        results = {}
        for name in experiment_names:
            results[name] = self.experiments[name].results()
        return results
