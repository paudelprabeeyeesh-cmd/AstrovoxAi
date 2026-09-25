from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class QualiaSimulation:
    quale_type: str
    simulated_intensity: float
    valence: float
    arousal: float
    binding_map: dict[str, float]
    timestamp: float = field(default_factory=time.time)
    raw_feel_texture: str = ""
    intentional_content: str = ""
    phenomenological_character: str = ""
    ineffability_score: float = 0.0
    infallibility_score: float = 0.0
    transparency_score: float = 0.0


class QualiaSimulator:
    def __init__(self, phenomenal_consciousness=None):
        from ..consciousness.phenomenal_consciousness import PhenomenalConsciousness
        self.phenomenal = phenomenal_consciousness or PhenomenalConsciousness()
        self.simulations: list[QualiaSimulation] = []
        self.quale_taxonomy: dict[str, dict[str, Any]] = {
            "visual_red": {"wavelength_range": (620, 750), "valence": 0.3, "arousal": 0.5},
            "pain_sharp": {"intensity_range": (0.7, 1.0), "valence": -0.9, "arousal": 0.9},
            "joy_warm": {"intensity_range": (0.4, 0.9), "valence": 0.9, "arousal": 0.6},
            "sorrow_deep": {"intensity_range": (0.3, 0.8), "valence": -0.8, "arousal": 0.3},
            "awe_vast": {"intensity_range": (0.5, 1.0), "valence": 0.7, "arousal": 0.8},
            "boredom_flat": {"intensity_range": (0.0, 0.3), "valence": -0.2, "arousal": 0.1},
            "anger_hot": {"intensity_range": (0.6, 1.0), "valence": -0.7, "arousal": 0.9},
            "serenity_calm": {"intensity_range": (0.2, 0.6), "valence": 0.6, "arousal": 0.2},
        }
        self.ineffability_models: dict[str, float] = {}
        self.qualia_binding_log: list[dict[str, Any]] = []

    def simulate_quale(self, quale_type: str, intensity: float, valence: float, arousal: float = 0.5, concepts: list[str] | None = None, description: str = "") -> QualiaSimulation:
        concepts = concepts or []
        taxonomy_entry = self.quale_taxonomy.get(quale_type, {})
        if taxonomy_entry:
            valence = taxonomy_entry.get("valence", valence)
            arousal = taxonomy_entry.get("arousal", arousal)
            intensity = max(taxonomy_entry.get("intensity_range", (0.0, 1.0))[0], min(intensity, taxonomy_entry.get("intensity_range", (1.0, 1.0))[1]))
        self.phenomenal.register_qualia(quale_type, intensity, valence, arousal, concepts)
        binding_map = {concept: intensity * 0.5 * (1.0 + valence) for concept in concepts} if concepts else {"raw_experience": intensity}
        ineffability = self._compute_ineffability(quale_type, intensity, concepts)
        infallibility = self._compute_infallibility(quale_type, intensity)
        transparency = self._compute_transparency(quale_type, concepts)
        simulation = QualiaSimulation(
            quale_type=quale_type,
            simulated_intensity=max(0.0, min(1.0, intensity)),
            valence=max(-1.0, min(1.0, valence)),
            arousal=max(0.0, min(1.0, arousal)),
            binding_map=binding_map,
            raw_feel_texture=description or f"simulated_{quale_type}_texture",
            intentional_content="; ".join(concepts) if concepts else "raw_experience",
            phenomenological_character=self._describe_phenomenology(quale_type, intensity, valence),
            ineffability_score=ineffability,
            infallibility_score=infallibility,
            transparency_score=transparency,
        )
        self.simulations.append(simulation)
        self.qualia_binding_log.append({
            "timestamp": time.time(),
            "quale_type": quale_type,
            "intensity": intensity,
            "valence": valence,
            "arousal": arousal,
            "concepts_bound": len(concepts),
        })
        return simulation

    def get_quale_report(self) -> dict[str, Any]:
        if not self.simulations:
            return {"status": "no_simulations"}
        latest = self.simulations[-1]
        return {
            "total_simulations": len(self.simulations),
            "recent": [s.quale_type for s in self.simulations[-5:]],
            "phenomenal_state": self.phenomenal.phenomenal_state(),
            "latest_quale": {
                "type": latest.quale_type,
                "intensity": round(latest.simulated_intensity, 4),
                "valence": round(latest.valence, 4),
                "arousal": round(latest.arousal, 4),
                "ineffability": round(latest.ineffability_score, 4),
                "infallibility": round(latest.infallibility_score, 4),
                "transparency": round(latest.transparency_score, 4),
            },
        }

    def compare_qualia(self, quale_a: str, quale_b: str) -> dict[str, Any]:
        sims_a = [s for s in self.simulations if s.quale_type == quale_a]
        sims_b = [s for s in self.simulations if s.quale_type == quale_b]
        if not sims_a or not sims_b:
            return {"error": "insufficient_data"}
        avg_a = self._average_simulation(sims_a)
        avg_b = self._average_simulation(sims_b)
        return {
            "quale_a": {
                "type": quale_a,
                "avg_intensity": round(avg_a["intensity"], 4),
                "avg_valence": round(avg_a["valence"], 4),
                "avg_arousal": round(avg_a["arousal"], 4),
            },
            "quale_b": {
                "type": quale_b,
                "avg_intensity": round(avg_b["intensity"], 4),
                "avg_valence": round(avg_b["valence"], 4),
                "avg_arousal": round(avg_b["arousal"], 4),
            },
            "similarity": round(
                1.0 - abs(avg_a["valence"] - avg_b["valence"]) / 2.0
                - abs(avg_a["intensity"] - avg_b["intensity"]),
                4,
            ),
        }

    def _compute_ineffability(self, quale_type: str, intensity: float, concepts: list[str]) -> float:
        base = 0.3 + 0.4 * intensity
        if not concepts:
            base += 0.2
        return min(1.0, base)

    def _compute_infallibility(self, quale_type: str, intensity: float) -> float:
        return max(0.0, min(1.0, 0.5 + 0.3 * intensity - 0.1))

    def _compute_transparency(self, quale_type: str, concepts: list[str]) -> float:
        return min(1.0, 0.2 + 0.1 * len(concepts))

    def _describe_phenomenology(self, quale_type: str, intensity: float, valence: float) -> str:
        if valence > 0.5:
            tone = "bright and expansive"
        elif valence < -0.5:
            tone = "dark and contracting"
        else:
            tone = "neutral and stable"
        return f"{quale_type} experience: {tone}, intensity {intensity:.2f}"

    def _average_simulation(self, sims: list[QualiaSimulation]) -> dict[str, float]:
        n = len(sims)
        return {
            "intensity": sum(s.simulated_intensity for s in sims) / n,
            "valence": sum(s.valence for s in sims) / n,
            "arousal": sum(s.arousal for s in sims) / n,
        }
