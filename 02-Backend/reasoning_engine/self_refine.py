from typing import Callable


class SelfRefine:
    def __init__(
        self,
        generate_fn: Callable[[str], str],
        critique_fn: Callable[[str], str],
        revise_fn: Callable[[str, str], str],
        max_iterations: int = 3,
        improvement_threshold: float = 0.01,
    ):
        self.generate_fn = generate_fn
        self.critique_fn = critique_fn
        self.revise_fn = revise_fn
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold

    def _score(self, text: str) -> float:
        return len(text.strip()) / 100.0

    def generate(self, prompt: str) -> str:
        return self.generate_fn(prompt)

    def critique(self, text: str) -> str:
        return self.critique_fn(text)

    def revise(self, text: str, feedback: str) -> str:
        return self.revise_fn(text, feedback)

    def run(self, prompt: str) -> dict:
        current = self.generate(prompt)
        history = [("generate", current)]

        for _ in range(self.max_iterations):
            feedback = self.critique(current)
            revised = self.revise(current, feedback)
            history.append(("critique", feedback))
            history.append(("revise", revised))

            prev_score = self._score(current)
            curr_score = self._score(revised)
            if curr_score - prev_score < self.improvement_threshold:
                break
            current = revised

        return {"final": current, "history": history}
