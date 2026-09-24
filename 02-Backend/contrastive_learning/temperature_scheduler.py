import numpy as np
from typing import Optional


class TemperatureScheduler:
    def __init__(
        self,
        initial_temperature: float = 0.07,
        min_temperature: float = 0.01,
        max_temperature: float = 1.0,
        schedule: str = "constant",
        step_size: int = 1000,
        gamma: float = 0.95,
    ):
        if initial_temperature <= 0 or initial_temperature > max_temperature:
            raise ValueError("initial_temperature must be in (0, max_temperature]")
        if min_temperature < 0 or max_temperature < min_temperature:
            raise ValueError("Invalid temperature bounds")

        self.initial_temperature = float(initial_temperature)
        self.temperature = float(initial_temperature)
        self.min_temperature = float(min_temperature)
        self.max_temperature = float(max_temperature)
        self.schedule = schedule.lower()
        self.step_size = step_size
        self.gamma = gamma
        self.step = 0

        valid_schedules = {"constant", "step", "exponential", "cosine"}
        if self.schedule not in valid_schedules:
            raise ValueError(f"schedule must be one of {valid_schedules}")

    def step(self) -> float:  # type: ignore[override]
        self.step += 1

        if self.schedule == "constant":
            pass
        elif self.schedule == "step":
            if self.step % self.step_size == 0:
                self.temperature = max(self.min_temperature, self.temperature * self.gamma)
        elif self.schedule == "exponential":
            self.temperature = max(
                self.min_temperature,
                self.initial_temperature * (self.gamma ** (self.step / self.step_size)),
            )
        elif self.schedule == "cosine":
            progress = min(1.0, self.step / max(self.step_size, 1))
            cosine_decay = 0.5 * (1.0 + np.cos(np.pi * progress))
            self.temperature = self.min_temperature + (self.initial_temperature - self.min_temperature) * cosine_decay
            self.temperature = max(self.min_temperature, min(self.max_temperature, self.temperature))

        return float(self.temperature)

    def get(self) -> float:
        return float(self.temperature)

    def reset(self) -> None:
        self.temperature = float(self.initial_temperature)
        self.step = 0
