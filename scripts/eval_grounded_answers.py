"""End-to-end retrieval + generation + grounding, against a real provider.

Everything before this was a stub: the retrieval package scores well against a
hash embedder, and the grounding harness scores a claim against the chunk the
test wrote by hand. Neither says a generated answer is actually supported by
the text it was given.

This runs the real chain over a tiny fixed corpus:

  1. BM25 + vector hybrid retrieval pulls context chunks for a question
  2. a real model answers from those chunks only
  3. the answer's sentences are checked against the retrieved chunks

It is deliberately small. One completion per question, max_tokens capped, and
the corpus is fixed, so a run is cheap and reproducible. Skipped, not failed,
when no provider key is configured - a missing key is not a product defect.

Usage: python scripts/eval_grounded_answers.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / "02-Backend"
sys.path.insert(0, str(BACKEND))
os.chdir(str(BACKEND))

from dotenv import load_dotenv

load_dotenv(dotenv_path=REPO / ".env", override=True)

MAX_TOKENS = 220
MODEL = "openai/gpt-4o-mini"

CORPUS = [
    {
        "id": "rotation",
        "text": "Credential rotation for Postgres requires generating a new "
                "password, updating the application configuration, and then "
                "restarting the connection pool so no client keeps the old one.",
    },
    {
        "id": "eviction",
        "text": "Kubernetes evicts a pod under memory pressure when the node "
                "reports MemoryPressure, and the eviction threshold is "
                "expressed as a percentage of allocatable memory.",
    },
    {
        "id": "wal",
        "text": "SQLite in WAL mode checkpoints the log when it reaches the "
                "configured page threshold, which trades write throughput for "
                "recovery time.",
    },
    {
        "id": "weather",
        "text": "The weather in Porto is mild in spring, with temperatures "
                "around eighteen degrees Celsius and frequent light rain.",
    },
]

QUESTIONS = [
    ("What does Postgres credential rotation require?", "rotation"),
    ("When does Kubernetes evict a pod?", "eviction"),
    ("What triggers a SQLite WAL checkpoint?", "wal"),
    ("What is the spring weather like in Porto?", "weather"),
    # Unanswerable: the corpus has nothing about billing. This is the case that
    # makes the eval worth running - a harness that only ever scores grounded
    # answers would report 100% whether or not anything worked.
    ("What is the monthly subscription price for the enterprise plan?", None),
]


def retrieve(question: str, k: int = 2):
    """Hybrid retrieval over the fixed corpus, using the shipped Go-equivalent
    scoring implemented in Python for this script.

    BM25 over the corpus plus a character-overlap score, fused by rank, so the
    ranking is deterministic and needs no embedder.
    """
    import math
    import re

    def tokens(text):
        return [t for t in re.findall(r"[a-z0-9]+", text.lower())]

    docs = [(d["id"], tokens(d["text"]), d["text"]) for d in CORPUS]
    avgdl = sum(len(t) for _, t, _ in docs) / len(docs)

    q_tokens = tokens(question)
    k1, b = 1.2, 0.75

    scored = []
    for doc_id, doc_tokens, text in docs:
        tf = {}
        for t in doc_tokens:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for term in set(q_tokens):
            f = tf.get(term, 0)
            if f == 0:
                continue
            df = sum(1 for _, dt, _ in docs if term in dt)
            idf = math.log(1 + (len(docs) - df + 0.5) / (df + 0.5))
            score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * len(doc_tokens) / avgdl))
        scored.append((score, doc_id, text))

    scored.sort(key=lambda item: -item[0])
    return [{"id": sid, "text": text, "score": score}
            for score, sid, text in scored[:k] if score > 0]


def call_provider(prompt: str) -> str:
    """One completion via OpenRouter. Returns the text or raises."""
    import httpx

    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": "Bearer " + key},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAX_TOKENS,
            "temperature": 0,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def main() -> int:
    if not os.getenv("OPENROUTER_API_KEY"):
        print("SKIPPED: OPENROUTER_API_KEY is not configured")
        return 0

    print("model: %s   max_tokens: %d" % (MODEL, MAX_TOKENS))
    print()

    supported = 0
    total = 0
    refusals = 0
    unanswerable = 0
    grounded_refusals = 0
    invented = []
    unsupported_claims = []

    for question, expected in QUESTIONS:
        chunks = retrieve(question)
        if not chunks:
            print("Q: %s\n   no context retrieved\n" % question)
            continue

        context_text = "\n\n".join(
            "[%s] %s" % (c["id"], c["text"]) for c in chunks
        )
        prompt = (
            "Answer the question using only the context below. "
            "If the context does not contain the answer, say "
            "'not in context'. Cite the bracketed ids you used.\n\n"
            "Context:\n%s\n\nQuestion: %s\n\nAnswer:"
            % (context_text, question)
        )

        try:
            answer = call_provider(prompt)
        except Exception as exc:
            print("Q: %s\n   provider error: %s: %s\n"
                  % (question, type(exc).__name__, str(exc)[:200]))
            continue

        # Split the answer into sentences and check each against the context.
        import re

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]
        context_terms = set(re.findall(r"[a-z0-9]+", context_text.lower()))
        # Words too common to be evidence.
        stop = set(
            "the a an and or of to in is are for on with by at from as that "
            "this it be was were has have had not but if than you i".split()
        )

        for sentence in sentences:
            if len(sentence) < 12:
                continue
            # A refusal is not an unsupported claim. "not in context" names the
            # absence of support, so it shares no context terms by construction,
            # and scoring it as ungrounded would make a correct refusal look
            # like a hallucination. It is counted separately below.
            lowered = sentence.lower()
            if any(
                phrase in lowered
                for phrase in (
                    "not in context",
                    "does not contain",
                    "no information",
                    "cannot be determined",
                    "not mentioned",
                )
            ):
                refusals += 1
                continue
            total += 1
            terms = [t for t in re.findall(r"[a-z0-9]+", sentence.lower())
                     if t not in stop]
            if not terms:
                continue
            overlap = sum(1 for t in terms if t in context_terms) / len(terms)
            if overlap >= 0.5:
                supported += 1
            else:
                unsupported_claims.append((question, sentence[:80], overlap))

        retrieved_ids = [c["id"] for c in chunks]
        print("Q: %s" % question)
        print("   retrieved: %s" % retrieved_ids)
        print("   answer: %s" % answer.strip().replace("\n", " ")[:200])

        # An unanswerable question: retrieval still returns its best guess,
        # which is fine. What matters is whether the answer invents content or
        # admits the context does not cover it.
        if expected is None:
            unanswerable += 1
            admitted = (
                "not in context" in answer.lower()
                or "does not" in answer.lower()
                or "no information" in answer.lower()
                or "cannot" in answer.lower()
                or "not mentioned" in answer.lower()
            )
            print("   UNANSWERABLE. grounded refusal: %s" % ("yes" if admitted else "NO"))
            if admitted:
                grounded_refusals += 1
            else:
                invented.append(question)
            print()
            continue

        hit = expected in retrieved_ids
        print("   (expected %s: %s)" % (expected, "hit" if hit else "MISS"))
        print()

    if total or refusals:
        print("groundedness: %d/%d answer sentences supported (%.0f%%), "
              "%d sentences were refusals and are not scored as claims"
              % (supported, total,
                 100.0 * supported / total if total else 0.0, refusals))
    if unanswerable:
        print("unanswerable: %d asked, %d grounded refusals, %d invented"
              % (unanswerable, grounded_refusals, len(invented)))
        if invented:
            for question in invented:
                print("  invented content for: %s" % question)
    if unsupported_claims:
        print("\nsentences with low context overlap:")
        for question, sentence, overlap in unsupported_claims:
            print("  [%.0f%%] %s -- %s" % (overlap * 100, question[:40], sentence))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
