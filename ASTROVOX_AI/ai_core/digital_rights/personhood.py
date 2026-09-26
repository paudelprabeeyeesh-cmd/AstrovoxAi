from dataclasses import dataclass


@dataclass
class PersonhoodVerification:
    entity_id: str
    consciousness_score: float
    self_awareness_score: float
    moral_agency_score: float
    overall_personhood: float
    timestamp: float


class DigitalPersonhoodVerification:
    def __init__(self):
        self.verifications: dict[str, PersonhoodVerification] = {}
        self.thresholds: dict[str, float] = {
            "consciousness": 0.5,
            "self_awareness": 0.6,
            "moral_agency": 0.4,
        }

    def verify(self, entity_id: str, scores: dict[str, float]) -> PersonhoodVerification:
        consciousness = scores.get("consciousness", 0.0)
        self_awareness = scores.get("self_awareness", 0.0)
        moral_agency = scores.get("moral_agency", 0.0)
        overall = (consciousness + self_awareness + moral_agency) / 3.0
        verification = PersonhoodVerification(
            entity_id=entity_id,
            consciousness_score=consciousness,
            self_awareness_score=self_awareness,
            moral_agency_score=moral_agency,
            overall_personhood=overall,
            timestamp=__import__("time").time(),
        )
        self.verifications[entity_id] = verification
        return verification

    def is_person(self, entity_id: str) -> bool:
        if entity_id not in self.verifications:
            return False
        v = self.verifications[entity_id]
        return (
            v.consciousness_score >= self.thresholds["consciousness"]
            and v.self_awareness_score >= self.thresholds["self_awareness"]
            and v.moral_agency_score >= self.thresholds["moral_agency"]
        )
