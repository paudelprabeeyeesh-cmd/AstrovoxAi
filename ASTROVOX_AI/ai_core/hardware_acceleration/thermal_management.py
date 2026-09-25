from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
import torch

logger = logging.getLogger(__name__)


class ThermalManager:
    def __init__(self, max_temp_c: float = 95.0, ambient_temp_c: float = 25.0):
        self.max_temp_c = max_temp_c
        self.ambient_temp_c = ambient_temp_c
        self.current_temp_c = ambient_temp_c
        self.thermal_zones: Dict[str, float] = {}
        self.cooling_capacity: Dict[str, float] = {}

    def read_temperature(self, zone: str = "gpu") -> float:
        return self.thermal_zones.get(zone, self.current_temp_c)

    def update_temperature(self, zone: str, temp_c: float) -> None:
        self.thermal_zones[zone] = temp_c
        self.current_temp_c = max(self.thermal_zones.values()) if self.thermal_zones else temp_c

    def is_throttling_required(self) -> bool:
        return self.current_temp_c >= self.max_temp_c

    def estimate_throttle_factor(self) -> float:
        if self.current_temp_c >= self.max_temp_c:
            return max(0.1, 1.0 - (self.current_temp_c - self.max_temp_c) / 50.0)
        return 1.0


class ThermalThrottlingController:
    def __init__(self, thermal_manager: ThermalManager, power_manager: Any):
        self.thermal_manager = thermal_manager
        self.power_manager = power_manager
        self.throttle_steps = 8

    def should_throttle(self) -> bool:
        return self.thermal_manager.is_throttling_required()

    def apply_throttle(self, current_freq_ghz: float) -> float:
        if not self.should_throttle():
            return current_freq_ghz
        factor = self.thermal_manager.estimate_throttle_factor()
        return current_freq_ghz * factor

    def step(self, current_freq_ghz: float) -> float:
        if self.should_throttle():
            return self.apply_throttle(current_freq_ghz)
        return current_freq_ghz


class CoolingOptimizer:
    def __init__(self, fan_curves: Optional[Dict[str, List[Tuple[float, float]]]] = None):
        self.fan_curves = fan_curves or {
            "gpu": [(30.0, 0.3), (50.0, 0.5), (70.0, 0.7), (85.0, 1.0)]
        }
        self.fan_speeds: Dict[str, float] = {}

    def optimize_fan_speed(self, zone: str, temp_c: float) -> float:
        curve = self.fan_curves.get(zone, [(30.0, 0.3), (85.0, 1.0)])
        fan_speed = 0.0
        for t, speed in curve:
            if temp_c >= t:
                fan_speed = speed
            else:
                break
        self.fan_speeds[zone] = fan_speed
        return fan_speed

    def estimate_cooling_effectiveness(self, temp_c: float, fan_speed: float) -> float:
        return max(0.0, min(1.0, fan_speed * (1.0 - (temp_c / 100.0))))
