"""Source Verification — verify credibility and trustworthiness of search results."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


TRUSTED_TLDS = {".gov", ".edu", ".ac.uk", ".ac.jp", ".ac.in"}
TRUSTED_DOMAINS = {
    "wikipedia.org": 0.9,
    "github.com": 0.85,
    "arxiv.org": 0.9,
    "semanticscholar.org": 0.9,
    "ieee.org": 0.9,
    "springer.com": 0.9,
    "nature.com": 0.95,
    "sciencedirect.com": 0.9,
    "ncbi.nlm.nih.gov": 0.95,
    "who.int": 0.95,
    "un.org": 0.9,
    "europa.eu": 0.9,
    "gov": 0.95,
    "edu": 0.9,
    "medium.com": 0.5,
    "youtube.com": 0.4,
    "youtu.be": 0.4,
    "reddit.com": 0.4,
    "quora.com": 0.3,
    "bilibili.com": 0.4,
    "tiktok.com": 0.2,
    "facebook.com": 0.3,
    "twitter.com": 0.4,
    "x.com": 0.4,
}

BLOCKED_PATTERNS = [
    re.compile(r"porn|xxx|adult|casino|bet|spam|malware|phishing", re.I),
]


def verify_source(url: str, source_type: str = "web") -> Tuple[float, bool]:
    if not url:
        return 0.0, False
    lower_url = url.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(lower_url):
            return 0.0, False
    score = 0.3
    verified = False
    if url.startswith("https://"):
        score += 0.1
    for domain, trust in TRUSTED_DOMAINS.items():
        if domain in lower_url:
            score = max(score, trust)
            if trust >= 0.8:
                verified = True
    if any(lower_url.endswith(tld) for tld in TRUSTED_TLDS):
        score = max(score, 0.9)
        verified = True
    if re.search(r"\d{4}", url):
        score += 0.05
    return min(score, 1.0), verified


def verify_sources_batch(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for r in results:
        url = r.get("url", "")
        source_type = r.get("source_type", "web")
        score, verified = verify_source(url, source_type)
        r["verification_score"] = round(score, 4)
        r["verified"] = verified
    return results


def get_verification_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not results:
        return {"verified_count": 0, "total_count": 0, "avg_score": 0.0}
    scores = [r.get("verification_score", 0.0) for r in results]
    verified_count = sum(1 for r in results if r.get("verified"))
    return {
        "verified_count": verified_count,
        "total_count": len(results),
        "avg_score": round(sum(scores) / len(scores), 4),
        "verification_rate": round(verified_count / len(results), 4),
    }
