import hashlib
import hmac
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Commitment:
    commitment: str
    opening: str


class ZeroKnowledgeProof:
    @staticmethod
    def commit(secret: str, nonce: Optional[str] = None) -> Commitment:
        nonce = nonce or os.urandom(32).hex()
        commitment = hashlib.sha256((secret + nonce).encode()).hexdigest()
        return Commitment(commitment=commitment, opening=nonce)

    @staticmethod
    def verify(commitment: str, secret: str, nonce: str) -> bool:
        expected = hashlib.sha256((secret + nonce).encode()).hexdigest()
        return hmac.compare_digest(expected, commitment)

    @staticmethod
    def prove(secret: str, witness: str) -> Dict[str, Any]:
        commitment = ZeroKnowledgeProof.commit(secret)
        challenge = hashlib.sha256((commitment.commitment + witness).encode()).hexdigest()[:8]
        response = hashlib.sha256((secret + challenge).encode()).hexdigest()
        return {"commitment": commitment.commitment, "challenge": challenge, "response": response}

    @staticmethod
    def verify_proof(proof: Dict[str, Any], public_input: str) -> bool:
        expected_challenge = hashlib.sha256((proof["commitment"] + public_input).encode()).hexdigest()[:8]
        if not hmac.compare_digest(expected_challenge, proof["challenge"]):
            return False
        expected_response = hashlib.sha256((public_input + proof["challenge"]).encode()).hexdigest()
        return hmac.compare_digest(expected_response, proof["response"])
