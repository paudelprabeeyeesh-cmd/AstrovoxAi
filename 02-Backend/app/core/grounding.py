import logging

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7
MAX_CITATION_DISTANCE = 0.85


def score_confidence(answer: str, contexts: list[dict], query: str) -> float:
    if not contexts:
        return 0.0

    best_score = max(c.get("score", 0.0) for c in contexts)
    if best_score < MAX_CITATION_DISTANCE:
        return 0.3

    answer_lower = answer.lower()
    query_terms = set(query.lower().split())
    matched_terms = sum(1 for term in query_terms if term in answer_lower)
    coverage = matched_terms / max(len(query_terms), 1)

    confidence = min(best_score, 0.5 + (coverage * 0.5))
    return round(confidence, 2)


def has_supporting_context(answer: str, contexts: list[dict]) -> bool:
    if not contexts:
        return False

    answer_words = set(answer.lower().split())
    for ctx in contexts:
        ctx_text = ctx.get("content", "").lower()
        overlap = len(answer_words & set(ctx_text.split()))
        if overlap >= 2:
            return True
    return False


def ground_answer(
    answer: str, contexts: list[dict], query: str
) -> tuple[str, bool, float]:
    confidence = score_confidence(answer, contexts, query)

    if not has_supporting_context(answer, contexts):
        logger.warning("No supporting context found for answer")
        return (
            "I don't know. There is no information in my knowledge base to answer this question.",
            True,
            confidence,
        )

    if confidence < CONFIDENCE_THRESHOLD:
        logger.warning(f"Low confidence answer: {confidence}")
        return "I don't know. I'm not confident enough in my answer.", True, confidence

    citations = [
        c.get("id", "")
        for c in contexts[:3]
        if c.get("score", 0) > MAX_CITATION_DISTANCE
    ]
    if citations:
        answer = f"{answer}\n\nSources: {', '.join(citations)}"

    return answer, False, confidence


def should_refuse(confidence: float) -> bool:
    return confidence < CONFIDENCE_THRESHOLD
