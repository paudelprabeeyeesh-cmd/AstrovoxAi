"""Injection defense package."""

from injection_defense.canary_tokens import (
    CanaryRegistry,
    CanaryToken,
    check_canary,
    create_canary,
    embed_canary,
    get_global_registry,
)
from injection_defense.defense_in_depth import (
    DefenseInDepth,
    DefenseLayer,
    DefenseResult,
)
from injection_defense.heuristic_detection import (
    InjectionMatch,
    detect_injection,
    is_injection,
)
from injection_defense.model_detection import (
    FeatureVector,
    InjectionClassifier,
)
from injection_defense.privilege_separation import (
    PrivilegedContent,
    TrustLevel,
    build_framed_prompt,
    enforce_boundary,
    validate_trust_level,
)
from injection_defense.role_reassertion import (
    ConversationBuffer,
    ReAssertionConfig,
    compress_prompt,
    estimate_tokens,
)

__all__ = [
    "CanaryRegistry",
    "CanaryToken",
    "check_canary",
    "create_canary",
    "embed_canary",
    "get_global_registry",
    "DefenseInDepth",
    "DefenseLayer",
    "DefenseResult",
    "InjectionMatch",
    "detect_injection",
    "is_injection",
    "FeatureVector",
    "InjectionClassifier",
    "PrivilegedContent",
    "TrustLevel",
    "build_framed_prompt",
    "enforce_boundary",
    "validate_trust_level",
    "ConversationBuffer",
    "ReAssertionConfig",
    "compress_prompt",
    "estimate_tokens",
]
