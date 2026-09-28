from __future__ import annotations

import torch
import torch.nn as nn

# ---------------------------------------------------------------------------
# 1. Embodied State Encoder
# ---------------------------------------------------------------------------


class EmbodiedStateEncoder(nn.Module):
    """Encodes multimodal embodied state (vision + proprioception + language)."""

    def __init__(
        self,
        vision_hidden_size: int = 768,
        proprio_dim: int = 32,
        text_hidden_size: int = 768,
        output_dim: int = 768,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.vision_proj = nn.Linear(vision_hidden_size, output_dim, device=device, dtype=dtype)
        self.proprio_proj = nn.Linear(proprio_dim, output_dim, device=device, dtype=dtype)
        self.text_proj = nn.Linear(text_hidden_size, output_dim, device=device, dtype=dtype)
        self.fusion = nn.Sequential(
            nn.LayerNorm(output_dim * 3, device=device, dtype=dtype),
            nn.Linear(output_dim * 3, output_dim, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(output_dim, output_dim, device=device, dtype=dtype),
        )

    def forward(
        self,
        vision_embeds: torch.Tensor | None = None,
        proprio: torch.Tensor | None = None,
        text_embeds: torch.Tensor | None = None,
    ) -> torch.Tensor:
        parts = []
        if vision_embeds is not None:
            parts.append(self.vision_proj(vision_embeds))
        if proprio is not None:
            parts.append(self.proprio_proj(proprio))
        if text_embeds is not None:
            parts.append(self.text_proj(text_embeds))
        if not parts:
            raise ValueError("At least one modality must be provided")
        fused = self.fusion(torch.cat(parts, dim=-1))
        return fused


# ---------------------------------------------------------------------------
# 2. Action Decoder
# ---------------------------------------------------------------------------


class ActionDecoder(nn.Module):
    """Decodes embodied actions from latent representations."""

    def __init__(
        self,
        input_dim: int = 768,
        action_dim: int = 7,
        hidden_size: int = 256,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, action_dim, device=device, dtype=dtype),
            nn.Tanh(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ---------------------------------------------------------------------------
# 3. Robot Control Interface
# ---------------------------------------------------------------------------


class RobotController:
    """High-level robot control interface."""

    def __init__(
        self,
        action_decoder: ActionDecoder,
        state_encoder: EmbodiedStateEncoder,
        max_action: float = 1.0,
        device: torch.device | None = None,
    ):
        self.action_decoder = action_decoder
        self.state_encoder = state_encoder
        self.max_action = max_action
        self.device = device or next(action_decoder.parameters()).device

    def act(
        self,
        vision_embeds: torch.Tensor | None = None,
        proprio: torch.Tensor | None = None,
        text_embeds: torch.Tensor | None = None,
    ) -> torch.Tensor:
        state = self.state_encoder(
            vision_embeds=vision_embeds, proprio=proprio, text_embeds=text_embeds
        )
        actions = self.action_decoder(state)
        return actions * self.max_action


# ---------------------------------------------------------------------------
# 4. Embodied Planning
# ---------------------------------------------------------------------------


class EmbodiedPlanner(nn.Module):
    """Task planning module for embodied AI."""

    def __init__(
        self,
        hidden_size: int = 768,
        num_steps: int = 10,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.num_steps = num_steps
        self.step_embeddings = nn.Embedding(num_steps, hidden_size, device=device, dtype=dtype)
        self.planner = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size, device=device, dtype=dtype),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype),
        )
        self.goal_proj = nn.Linear(hidden_size, hidden_size, device=device, dtype=dtype)

    def forward(self, goal_embedding: torch.Tensor) -> torch.Tensor:
        B = goal_embedding.size(0)
        plans = []
        for step in range(self.num_steps):
            step_emb = self.step_embeddings(
                torch.tensor([step], device=goal_embedding.device)
            ).expand(B, -1)
            combined = torch.cat([goal_embedding, step_emb], dim=-1)
            plan_step = self.planner(combined)
            plans.append(plan_step)
        return torch.stack(plans, dim=1)


# ---------------------------------------------------------------------------
# 5. Robotics Transformer
# ---------------------------------------------------------------------------


class RoboticsTransformer(nn.Module):
    """End-to-end robotics transformer combining perception and action."""

    def __init__(
        self,
        vision_hidden_size: int = 768,
        proprio_dim: int = 32,
        text_hidden_size: int = 768,
        action_dim: int = 7,
        hidden_size: int = 768,
        num_layers: int = 8,
        num_attention_heads: int = 12,
        max_plan_steps: int = 10,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.state_encoder = EmbodiedStateEncoder(
            vision_hidden_size=vision_hidden_size,
            proprio_dim=proprio_dim,
            text_hidden_size=text_hidden_size,
            output_dim=hidden_size,
            device=device,
            dtype=dtype,
        )
        self.planner = EmbodiedPlanner(
            hidden_size=hidden_size, num_steps=max_plan_steps, device=device, dtype=dtype,
        )
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size, nhead=num_attention_heads, batch_first=True,
            device=device, dtype=dtype,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.action_decoder = ActionDecoder(
            input_dim=hidden_size, action_dim=action_dim, device=device, dtype=dtype,
        )

    def forward(
        self,
        vision_embeds: torch.Tensor | None = None,
        proprio: torch.Tensor | None = None,
        text_embeds: torch.Tensor | None = None,
        goal_embedding: torch.Tensor | None = None,
    ) -> torch.Tensor:
        state = self.state_encoder(
            vision_embeds=vision_embeds, proprio=proprio, text_embeds=text_embeds
        )
        if goal_embedding is not None:
            plan = self.planner(goal_embedding)
            state = torch.cat([state.unsqueeze(1), plan], dim=1)
        state = self.transformer(state)
        actions = self.action_decoder(state)
        return actions
