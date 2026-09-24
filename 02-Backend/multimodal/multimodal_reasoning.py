import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class Evidence:
    modality: str
    content: str
    confidence: float
    embedding: np.ndarray
    source: str = "unknown"


@dataclass
class ReasoningStep:
    step_id: int
    observation: str
    inference: str
    evidence_ids: List[str]
    confidence: float


class MultimodalReasoner:
    def __init__(self, embed_dim: int = 256):
        self.embed_dim = embed_dim
        self._rng = np.random.default_rng(42)
        self.evidence_store: Dict[str, Evidence] = {}
        self.reasoning_chain: List[ReasoningStep] = []
        self._step_counter = 0

    def add_evidence(self, evidence: Evidence) -> str:
        evidence_id = f"ev_{self._step_counter}"
        self._step_counter += 1
        self.evidence_store[evidence_id] = evidence
        return evidence_id

    def add_text_evidence(self, text: str, source: str = "text", confidence: float = 0.9) -> str:
        vec = self._text_to_embedding(text)
        evidence = Evidence(
            modality="text",
            content=text,
            confidence=confidence,
            embedding=vec,
            source=source,
        )
        return self.add_evidence(evidence)

    def add_image_evidence(self, pixels: np.ndarray, caption: str, source: str = "image", confidence: float = 0.85) -> str:
        vec = self._image_to_embedding(pixels)
        evidence = Evidence(
            modality="image",
            content=caption,
            confidence=confidence,
            embedding=vec,
            source=source,
        )
        return self.add_evidence(evidence)

    def _text_to_embedding(self, text: str) -> np.ndarray:
        vec = np.zeros(self.embed_dim, dtype=np.float64)
        tokens = text.lower().split()
        for idx, token in enumerate(tokens):
            h = hash(token) % self.embed_dim
            vec[h] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def _image_to_embedding(self, pixels: np.ndarray) -> np.ndarray:
        if pixels.ndim == 3:
            pixels = pixels.mean(axis=2)
        vec = np.zeros(self.embed_dim, dtype=np.float64)
        h, w = pixels.shape
        for i in range(4):
            for j in range(4):
                y1, x1 = i * h // 4, j * w // 4
                y2, x2 = (i + 1) * h // 4, (j + 1) * w // 4
                block = pixels[y1:y2, x1:x2]
                vec[i * 4 + j] = block.mean() / 255.0
        return vec / (np.linalg.norm(vec) + 1e-8)

    def reason(self, question: str, max_steps: int = 5) -> Dict[str, Any]:
        self.reasoning_chain = []
        current_hypothesis = question
        used_evidence = set()
        for step in range(max_steps):
            relevant = self._retrieve_relevant_evidence(current_hypothesis, top_k=3)
            if not relevant:
                break
            inference = self._synthesize_inference(current_hypothesis, relevant)
            evidence_ids = [ev_id for ev_id, _ in relevant]
            used_evidence.update(evidence_ids)
            reasoning_step = ReasoningStep(
                step_id=step,
                observation=current_hypothesis,
                inference=inference,
                evidence_ids=evidence_ids,
                confidence=float(np.mean([self.evidence_store[eid].confidence for eid in evidence_ids])),
            )
            self.reasoning_chain.append(reasoning_step)
            current_hypothesis = inference
        conclusion = self._form_conclusion()
        return {
            "conclusion": conclusion,
            "chain": [
                {
                    "step": rs.step_id,
                    "observation": rs.observation,
                    "inference": rs.inference,
                    "confidence": rs.confidence,
                }
                for rs in self.reasoning_chain
            ],
            "used_evidence_count": len(used_evidence),
        }

    def _retrieve_relevant_evidence(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        query_vec = self._text_to_embedding(query)
        scored = []
        for ev_id, evidence in self.evidence_store.items():
            sim = float(np.dot(query_vec, evidence.embedding))
            scored.append((ev_id, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _synthesize_inference(self, hypothesis: str, evidence: List[Tuple[str, float]]) -> str:
        texts = [self.evidence_store[eid].content for eid, _ in evidence]
        return f"Based on evidence, {hypothesis} is supported by: {texts[0] if texts else 'no direct evidence'}."

    def _form_conclusion(self) -> str:
        if not self.reasoning_chain:
            return "Insufficient evidence to form a conclusion."
        final_step = self.reasoning_chain[-1]
        confidence = final_step.confidence
        if confidence > 0.7:
            return f"Conclusion (high confidence): {final_step.inference}"
        return f"Conclusion (low confidence): {final_step.inference} Additional verification recommended."

    def chain_of_thought(self, question: str, context: Optional[str] = None) -> Dict[str, Any]:
        steps = []
        cot_prompt = f"Question: {question}\n"
        if context:
            cot_prompt += f"Context: {context}\n"
        cot_prompt += "Let's think step by step:\n"
        step1 = f"First, I identify the key entities and concepts in: {question}"
        steps.append(step1)
        step2 = "Next, I recall relevant knowledge from the evidence store."
        steps.append(step2)
        relevant = self._retrieve_relevant_evidence(question, top_k=2)
        if relevant:
            step3 = f"Supporting evidence: {self.evidence_store[relevant[0][0]].content}"
        else:
            step3 = "No supporting evidence found in the store."
        steps.append(step3)
        step4 = f"Therefore, the answer is based on the available evidence."
        steps.append(step4)
        return {
            "question": question,
            "chain_of_thought": steps,
            "final_answer": step4,
        }
