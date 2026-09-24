from dataclasses import dataclass, field
from typing import List, Optional, Dict
import random


@dataclass
class Character:
    name: str
    archetype: str
    motivation: str
    traits: List[str] = field(default_factory=list)


@dataclass
class Plot:
    title: str
    structure: str
    stages: List[str] = field(default_factory=list)
    coherence: float = 0.0


class NarrativeDesigner:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self.archetypes = ["hero", "mentor", "trickster", "shadow", "herald", "threshold guardian"]
        self.structures = ["three_act", "hero_journey", "kishotenketsu", "in_medias_res", "parallel"]

    def design(self, theme: str, characters: int = 3, structure: Optional[str] = None) -> Plot:
        if structure is None:
            structure = random.choice(self.structures)
        stages = self._stages(structure)
        stages_text = self._weave(theme, stages, characters)
        coherence = self._coherence(stages_text)
        title = self._title(theme)
        return Plot(title=title, structure=structure, stages=stages_text, coherence=coherence)

    def _stages(self, structure: str) -> List[str]:
        if structure == "three_act":
            return ["setup", "confrontation", "resolution"]
        if structure == "hero_journey":
            return ["call_to_adventure", "trials", "return"]
        if structure == "kishotenketsu":
            return ["introduction", "development", "twist", "resolution"]
        if structure == "in_medias_res":
            return ["midpoint_action", "backstory", "climax", "denouement"]
        return ["parallel_a", "parallel_b", "convergence"]

    def _weave(self, theme: str, stages: List[str], character_count: int) -> List[str]:
        result = []
        chars = self._characters(theme, character_count)
        for i, stage in enumerate(stages):
            char_notes = ", ".join(c.name for c in chars[:2])
            if stage in {"setup", "introduction", "call_to_adventure", "midpoint_action"}:
                result.append(f"{stage.capitalize()} of {theme}: {chars[0].name} faces {theme} alongside {char_notes}.")
            elif stage in {"confrontation", "trials", "development", "backstory"}:
                result.append(f"{stage.capitalize()} reveals tension in {theme} as {chars[-1].name} opposes {chars[0].name}.")
            elif stage == "twist":
                result.append(f"Twist: {chars[1].name} reveals a hidden layer of {theme}.")
            else:
                result.append(f"{stage.capitalize()} settles {theme} through {chars[0].archetype} and {chars[-1].archetype}.")
        return result

    def _characters(self, theme: str, count: int) -> List[Character]:
        names = ["Aria", "Orion", "Lyra", "Zara", "Kael", "Nova", "Riven", "Sable"]
        random.shuffle(names)
        chars = []
        for i in range(min(count, len(names))):
            archetype = self.archetypes[i % len(self.archetypes)]
            chars.append(Character(
                name=names[i],
                archetype=archetype,
                motivation=f"drive {theme} forward",
                traits=["curious", "resilient", "cunning", "empathetic", "ambitious", "loyal"][: (i + 1) % 3 + 1],
            ))
        return chars

    def _coherence(self, stages: List[str]) -> float:
        if not stages:
            return 0.0
        words = [w.lower() for s in stages for w in s.split()]
        unique = len(set(words))
        total = len(words)
        richness = unique / max(total, 1)
        length_score = 1.0 if all(8 <= len(s.split()) <= 40 for s in stages) else 0.7
        return max(0.0, min(1.0, 0.6 * richness + 0.4 * length_score))

    def _title(self, theme: str) -> str:
        prefixes = ["The", "Echoes of", "Shadows over", "Light beyond", "Whispers of", "Fragments of"]
        suffixes = ["Destiny", "the Veil", "Silence", "the Unknown", "Tomorrow", "Legacy"]
        return f"{random.choice(prefixes)} {theme} {random.choice(suffixes)}"
