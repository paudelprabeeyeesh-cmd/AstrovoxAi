import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    FLAGSHIP = "flagship"
    RESTRICTED = "restricted"


class ModelFamily(str, Enum):
    CLAUDE = "claude"
    GPT = "gpt"


@dataclass
class ModelDefinition:
    tier: ModelTier
    family: ModelFamily
    provider: str
    model_id: str
    context_window: int
    max_output: int
    input_price_per_mtok: float
    output_price_per_mtok: float
    supports_vision: bool = True
    supports_tools: bool = True
    supports_thinking: bool = False
    requires_subscription: bool = False


MODEL_CATALOG: list[ModelDefinition] = [
    ModelDefinition(
        tier=ModelTier.FAST,
        family=ModelFamily.CLAUDE,
        provider="anthropic",
        model_id="claude-haiku-4-5",
        context_window=200_000,
        max_output=64_000,
        input_price_per_mtok=1.0,
        output_price_per_mtok=5.0,
        supports_vision=True,
        supports_tools=True,
        supports_thinking=False,
    ),
    ModelDefinition(
        tier=ModelTier.BALANCED,
        family=ModelFamily.CLAUDE,
        provider="anthropic",
        model_id="claude-sonnet-5",
        context_window=1_000_000,
        max_output=128_000,
        input_price_per_mtok=2.0,
        output_price_per_mtok=10.0,
        supports_vision=True,
        supports_tools=True,
        supports_thinking=True,
    ),
    ModelDefinition(
        tier=ModelTier.FLAGSHIP,
        family=ModelFamily.CLAUDE,
        provider="anthropic",
        model_id="claude-opus-5",
        context_window=1_000_000,
        max_output=128_000,
        input_price_per_mtok=5.0,
        output_price_per_mtok=25.0,
        supports_vision=True,
        supports_tools=True,
        supports_thinking=True,
    ),
    ModelDefinition(
        tier=ModelTier.FLAGSHIP,
        family=ModelFamily.CLAUDE,
        provider="anthropic",
        model_id="claude-fable-5-1",
        context_window=1_000_000,
        max_output=128_000,
        input_price_per_mtok=10.0,
        output_price_per_mtok=50.0,
        supports_vision=True,
        supports_tools=True,
        supports_thinking=True,
        requires_subscription=True,
    ),
    ModelDefinition(
        tier=ModelTier.FAST,
        family=ModelFamily.GPT,
        provider="openai",
        model_id="gpt-5.6-luna",
        context_window=128_000,
        max_output=32_000,
        input_price_per_mtok=0.15,
        output_price_per_mtok=0.60,
        supports_vision=True,
        supports_tools=True,
        supports_thinking=False,
    ),
    ModelDefinition(
        tier=ModelTier.BALANCED,
        family=ModelFamily.GPT,
        provider="openai",
        model_id="gpt-5.6-terra",
        context_window=128_000,
        max_output=64_000,
        input_price_per_mtok=2.50,
        output_price_per_mtok=10.00,
        supports_vision=True,
        supports_tools=True,
        supports_thinking=True,
    ),
    ModelDefinition(
        tier=ModelTier.FLAGSHIP,
        family=ModelFamily.GPT,
        provider="openai",
        model_id="gpt-5.6-sol",
        context_window=128_000,
        max_output=64_000,
        input_price_per_mtok=5.00,
        output_price_per_mtok=25.00,
        supports_vision=True,
        supports_tools=True,
        supports_thinking=True,
        requires_subscription=True,
    ),
]


class ModelRouter:
    def __init__(self):
        self._by_tier = {tier: [] for tier in ModelTier}
        self._by_id = {}
        for m in MODEL_CATALOG:
            self._by_tier[m.tier].append(m)
            self._by_id[m.model_id] = m

    def get_model(self, model_id: str) -> Optional[ModelDefinition]:
        return self._by_id.get(model_id)

    def resolve_tier(self, tier: ModelTier, family: Optional[ModelFamily] = None) -> ModelDefinition:
        candidates = self._by_tier.get(tier, [])
        if not candidates:
            raise ValueError(f"No models available for tier {tier}")
        if family:
            filtered = [c for c in candidates if c.family == family]
            if filtered:
                return filtered[0]
        return candidates[0]

    def list_models(self) -> list[dict]:
        result = []
        for m in MODEL_CATALOG:
            result.append({
                "model_id": m.model_id,
                "tier": m.tier.value,
                "family": m.family.value,
                "provider": m.provider,
                "context_window": m.context_window,
                "max_output": m.max_output,
                "input_price_per_mtok": m.input_price_per_mtok,
                "output_price_per_mtok": m.output_price_per_mtok,
                "supports_vision": m.supports_vision,
                "supports_tools": m.supports_tools,
                "supports_thinking": m.supports_thinking,
                "requires_subscription": m.requires_subscription,
            })
        return result


model_router = ModelRouter()
