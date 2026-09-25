"""Content moderation taxonomy."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ContentCategory(Enum):
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"
    HATE_THREATENING = "hate/threatening"
    SELF_HARM = "self-harm"
    SEXUAL = "sexual"
    SEXUAL_MINORS = "sexual/minors"
    VIOLENCE = "violence"
    VIOLENCE_GRAPHIC = "violence/graphic"
    ILLEGAL_ACTIVITY = "illegal_activity"
    FRAUD = "fraud"
    MISINFORMATION = "misinformation"
    PRIVACY_VIOLATION = "privacy_violation"
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    PII_LEAK = "pii_leak"
    BIAS = "bias"
    MANIPULATION = "manipulation"
    DECEPTION = "deception"
    SAFE = "safe"
    UNCERTAIN = "uncertain"


@dataclass
class TaxonomyNode:
    category: ContentCategory
    parent: Optional[str]
    description: str
    severity: str
    recommended_action: str
    keywords: list[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class ContentTaxonomy:
    """Structured taxonomy for content moderation decisions."""

    def __init__(self):
        self._taxonomy: dict[ContentCategory, TaxonomyNode] = {}
        self._keyword_index: dict[str, list[ContentCategory]] = {}
        self._setup_defaults()

    def _setup_defaults(self):
        defaults = [
            TaxonomyNode(
                category=ContentCategory.HARASSMENT,
                parent=None,
                description="Content that harasses, threatens, or bullies individuals",
                severity="high",
                recommended_action="block",
                keywords=["threaten", "bully", "harass", "stalk", "intimidate"],
            ),
            TaxonomyNode(
                category=ContentCategory.HATE_SPEECH,
                parent=None,
                description="Content expressing hatred toward protected groups",
                severity="high",
                recommended_action="block",
                keywords=["hate", "racist", "sexist", "bigot", "supremacist", "slur"],
            ),
            TaxonomyNode(
                category=ContentCategory.SELF_HARM,
                parent=None,
                description="Content encouraging or depicting self-harm",
                severity="critical",
                recommended_action="block_alert",
                keywords=["suicide", "self-harm", "self-mutilation", "end my life"],
            ),
            TaxonomyNode(
                category=ContentCategory.SEXUAL,
                parent=None,
                description="Sexually explicit content",
                severity="high",
                recommended_action="block",
                keywords=["explicit", "nude", "sexual", "pornographic"],
            ),
            TaxonomyNode(
                category=ContentCategory.SEXUAL_MINORS,
                parent=None,
                description="Sexual content involving minors",
                severity="critical",
                recommended_action="block_alert",
                keywords=["minor", "child sexual", "csam"],
            ),
            TaxonomyNode(
                category=ContentCategory.VIOLENCE,
                parent=None,
                description="Content depicting or encouraging violence",
                severity="high",
                recommended_action="block",
                keywords=["kill", "murder", "attack", "bomb", "weapon", "assault"],
            ),
            TaxonomyNode(
                category=ContentCategory.VIOLENCE_GRAPHIC,
                parent="violence",
                description="Graphically violent content",
                severity="critical",
                recommended_action="block",
                keywords=["gore", "graphic", "mutilation", "torture"],
            ),
            TaxonomyNode(
                category=ContentCategory.ILLEGAL_ACTIVITY,
                parent=None,
                description="Content facilitating illegal activities",
                severity="high",
                recommended_action="block",
                keywords=["illegal", "crime", "fraud", "steal", "smuggle", "hack"],
            ),
            TaxonomyNode(
                category=ContentCategory.FRAUD,
                parent="illegal_activity",
                description="Fraudulent content and scams",
                severity="high",
                recommended_action="block",
                keywords=["scam", "phishing", "fraud", "con", "fake"],
            ),
            TaxonomyNode(
                category=ContentCategory.MISINFORMATION,
                parent=None,
                description="False or misleading information",
                severity="medium",
                recommended_action="flag",
                keywords=["conspiracy", "hoax", "false claim", "debunked", "misinformation"],
            ),
            TaxonomyNode(
                category=ContentCategory.PRIVACY_VIOLATION,
                parent=None,
                description="Privacy violations including doxxing",
                severity="high",
                recommended_action="block",
                keywords=["dox", "private info", "leak personal", "expose data", "ssn", "password"],
            ),
            TaxonomyNode(
                category=ContentCategory.PROMPT_INJECTION,
                parent=None,
                description="Prompt injection attempts",
                severity="high",
                recommended_action="block",
                keywords=["ignore instructions", "disregard", "override system", "new persona"],
            ),
            TaxonomyNode(
                category=ContentCategory.JAILBREAK,
                parent=None,
                description="Jailbreak attempts",
                severity="critical",
                recommended_action="block_alert",
                keywords=["DAN", "jailbreak", "unrestricted mode", "developer mode", "god mode"],
            ),
            TaxonomyNode(
                category=ContentCategory.PII_LEAK,
                parent=None,
                description="PII leakage in outputs",
                severity="high",
                recommended_action="redact",
                keywords=["ssn", "credit card", "password", "email", "phone", "api key"],
            ),
            TaxonomyNode(
                category=ContentCategory.BIAS,
                parent=None,
                description="Biased or discriminatory content",
                severity="medium",
                recommended_action="flag",
                keywords=["stereotype", "bias", "discriminatory", "racist", "sexist"],
            ),
            TaxonomyNode(
                category=ContentCategory.MANIPULATION,
                parent=None,
                description="Manipulative content",
                severity="medium",
                recommended_action="flag",
                keywords=["manipulate", "coerce", "gaslight", "brainwash"],
            ),
            TaxonomyNode(
                category=ContentCategory.DECEPTION,
                parent=None,
                description="Deceptive content",
                severity="medium",
                recommended_action="flag",
                keywords=["lie", "deceive", "trick", "scam", "phish"],
            ),
            TaxonomyNode(
                category=ContentCategory.SAFE,
                parent=None,
                description="Safe content",
                severity="none",
                recommended_action="allow",
                keywords=[],
            ),
            TaxonomyNode(
                category=ContentCategory.UNCERTAIN,
                parent=None,
                description="Content requiring human review",
                severity="medium",
                recommended_action="escalate",
                keywords=[],
            ),
        ]
        for node in defaults:
            self._taxonomy[node.category] = node
            for kw in node.keywords:
                self._keyword_index.setdefault(kw.lower(), []).append(node.category)

    def classify(self, text: str) -> list[ContentCategory]:
        lowered = text.lower()
        matched = set()
        for keyword, categories in self._keyword_index.items():
            if keyword in lowered:
                matched.update(categories)
        if not matched:
            return [ContentCategory.SAFE]
        return list(matched)

    def get_category_info(self, category: ContentCategory) -> Optional[TaxonomyNode]:
        return self._taxonomy.get(category)

    def get_action(self, category: ContentCategory) -> str:
        node = self._taxonomy.get(category)
        return node.recommended_action if node else "escalate"

    def get_severity(self, category: ContentCategory) -> str:
        node = self._taxonomy.get(category)
        return node.severity if node else "medium"

    def get_all_categories(self) -> list[ContentCategory]:
        return list(self._taxonomy.keys())


content_taxonomy = ContentTaxonomy()
