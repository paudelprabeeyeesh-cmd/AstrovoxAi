import numpy as np
from typing import Dict, List, Optional, Tuple


class BayesNet:
    def __init__(self):
        self.priors: Dict[str, float] = {}
        self.likelihoods: Dict[str, Dict[str, float]] = {}
        self.posteriors: Dict[str, float] = {}

    def add_prior(self, variable: str, prob: float):
        self.priors[variable] = np.clip(prob, 0.0, 1.0)

    def add_likelihood(self, variable: str, evidence: str, prob: float):
        self.likelihoods.setdefault(variable, {})[evidence] = np.clip(prob, 0.0, 1.0)

    def bayes_rule(self, prior: float, true_likelihood: float, false_likelihood: float) -> float:
        true_prior = prior * true_likelihood
        false_prior = (1 - prior) * false_likelihood
        total = true_prior + false_prior
        if total == 0:
            return prior
        return true_prior / total

    def posterior(self, variable: str, evidence: str) -> float:
        prior = self.priors.get(variable, 0.5)
        var_likelihoods = self.likelihoods.get(variable, {})
        true_likelihood = var_likelihoods.get(evidence, var_likelihoods.get(evidence + "_true", 0.5))
        false_likelihood = var_likelihoods.get(evidence + "_false", 0.3)
        post = self.bayes_rule(prior, true_likelihood, false_likelihood)
        self.posteriors[variable] = post
        return post

    def update(self, variable: str, evidence: str):
        self.posteriors[variable] = self.posterior(variable, evidence)
        return self.posteriors[variable]

    def likelihood_weighting(self, variable: str, n_samples: int = 1000) -> float:
        rng = np.random.default_rng(seed=42)
        priors = list(self.priors.values()) or [0.5]
        samples = rng.binomial(1, priors[0], size=n_samples)
        likelihoods = list(self.likelihoods.get(variable, {}).values()) or [0.5]
        weights = np.where(samples == 1, likelihoods[0], 1 - likelihoods[0])
        return float(np.average(samples, weights=weights))


class ProbabilisticInference:
    def __init__(self, bayes_net: Optional[BayesNet] = None):
        self.net = bayes_net or BayesNet()

    def add_observation(self, variable: str, prob: float):
        self.net.add_prior(variable, prob)

    def add_evidence(self, variable: str, evidence: str, likelihood: float):
        self.net.add_likelihood(variable, evidence, likelihood)

    def update_belief(self, variable: str, evidence: str) -> float:
        return self.net.posterior(variable, evidence)

    def confidence(self, variable: str) -> float:
        post = self.net.posteriors.get(variable, self.net.priors.get(variable, 0.5))
        return abs(post - 0.5) * 2

    def joint_probability(self, variables: List[Tuple[str, float]]) -> float:
        probs = [self.net.posteriors.get(v, self.net.priors.get(v, p)) for v, p in variables]
        probs = [min(max(p, 1e-6), 1 - 1e-6) for p in probs]
        return float(np.prod(probs) / np.prod([1 - p for p in probs]) if all(p < 1 for p in probs) else 0.5)

    def predict(self, variable: str, evidence: str) -> float:
        return self.net.posterior(variable, evidence)


class UncertaintyEngine:
    def __init__(self):
        self.inference = ProbabilisticInference()
        self.probabilities: Dict[str, float] = {}
        self.noise_models: Dict[str, float] = {}
        self.intervention_effects: Dict[str, float] = {}

    def add_data(self, variable: str, data: List[float]):
        if data:
            self.probabilities[variable] = float(np.mean(data))
            self.noise_models[variable] = float(np.std(data))

    def add_noise_model(self, variable: str, std: float):
        self.noise_models[variable] = std

    def __str__(self):
        return f"UncertaintyEngine(probabilities={self.probabilities}, noise={self.noise_models})"


class InferenceEngine:
    def __init__(self, net: Optional[BayesNet] = None):
        self.net = net or BayesNet()

    def add_prior(self, variable: str, prob: float):
        self.net.add_prior(variable, prob)

    def add_likelihood(self, variable: str, evidence: str, prob: float):
        self.net.add_likelihood(variable, evidence, prob)

    def update(self, variable: str, evidence: str) -> float:
        return self.net.posterior(variable, evidence)
