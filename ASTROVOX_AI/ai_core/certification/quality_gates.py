from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ModelCertification:
    model_id: str
    gates: List[Dict[str, Any]] = field(default_factory=list)
    certified: bool = False


class CertificationEngine:
    def __init__(self):
        self.certifications: Dict[str, ModelCertification] = {}

    def evaluate(self, model_id: str, gates: List[Dict[str, Any]]) -> ModelCertification:
        cert = ModelCertification(model_id=model_id, gates=gates)
        cert.certified = all(g.get("passed", False) for g in gates)
        self.certifications[model_id] = cert
        return cert
