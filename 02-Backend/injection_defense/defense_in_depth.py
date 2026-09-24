"""Defense in Depth: layers multiple defenses with no single point of failure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from injection_defense.canary_tokens import CanaryRegistry, check_canary, create_canary
from injection_defense.heuristic_detection import detect_injection, is_injection
from injection_defense.model_detection import InjectionClassifier
from injection_defense.privilege_separation import (
    PrivilegedContent,
    TrustLevel,
    build_framed_prompt,
    enforce_boundary,
    validate_trust_level,
)
from injection_defense.role_reassertion import (
    ReAssertionConfig,
    ConversationBuffer,
)


@dataclass
class DefenseLayer:
    name: str
    enabled: bool = True
    priority: int = 0
    check: Callable[[str], bool] = lambda text: False
    sanitize: Callable[[str], str] = lambda text: text


@dataclass
class DefenseResult:
    is_safe: bool
    layers_triggered: list[str]
    sanitized_text: str
    risk_score: float
    metadata: dict = field(default_factory=dict)


class DefenseInDepth:
    def __init__(self, classifier: InjectionClassifier | None = None) -> None:
        self.classifier = classifier or InjectionClassifier()
        self.canary_registry = CanaryRegistry()
        self._layers: list[DefenseLayer] = []
        self._register_default_layers()

    def _register_default_layers(self) -> None:
        self.register_layer(DefenseLayer(
            name="privilege_boundary",
            priority=0,
            check=lambda text: False,
            sanitize=lambda text: text,
        ))
        self.register_layer(DefenseLayer(
            name="heuristic",
            priority=1,
            check=is_injection,
            sanitize=lambda text: text,
        ))
        self.register_layer(DefenseLayer(
            name="model",
            priority=2,
            check=lambda text: self.classifier.predict(text),
            sanitize=lambda text: text,
        ))
        self.register_layer(DefenseLayer(
            name="canary",
            priority=3,
            check=check_canary,
            sanitize=lambda text: text,
        ))

    def register_layer(self, layer: DefenseLayer) -> None:
        self._layers.append(layer)
        self._layers.sort(key=lambda l: l.priority)

    def analyze(self, text: str) -> DefenseResult:
        layers_triggered: list[str] = []
        sanitized = text
        risk = 0.0

        for layer in self._layers:
            if not layer.enabled:
                continue
            if layer.check(text):
                layers_triggered.append(layer.name)
                risk = max(risk, 0.8 if layer.name in ("heuristic", "model") else 0.5)
                sanitized = layer.sanitize(sanitized)

        is_safe = len(layers_triggered) == 0
        return DefenseResult(
            is_safe=is_safe,
            layers_triggered=layers_triggered,
            sanitized_text=sanitized,
            risk_score=risk,
            metadata={"layer_count": len(self._layers)},
        )

    def protect(self, text: str, trust: TrustLevel = TrustLevel.UNTRUSTED) -> tuple[str, DefenseResult]:
        boundary_checked = enforce_boundary(text, trust)
        result = self.analyze(boundary_checked)
        return result.sanitized_text, result

    def full_pipeline(
        self,
        system_prompt: str,
        user_input: str,
        tool_outputs: Sequence[str],
    ) -> tuple[list[dict], DefenseResult]:
        system_content = PrivilegedContent(system_prompt, TrustLevel.SYSTEM, "system")
        user_content = PrivilegedContent(user_input, TrustLevel.UNTRUSTED, "user")
        tool_contents = [
            PrivilegedContent(t, TrustLevel.TOOL_OUTPUT, f"tool_{i}")
            for i, t in enumerate(tool_outputs)
        ]
        prompt = build_framed_prompt([system_content, user_content, *tool_contents])
        protected, result = self.protect(prompt)
        buffer = ConversationBuffer(
            config=ReAssertionConfig(
                system_prompt=system_prompt,
                max_context_tokens=8000,
                reassert_interval=5,
            )
        )
        buffer.add_message("user", protected)
        return buffer.get_context(), result
