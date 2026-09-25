"""
AstroVoxTransformer -- a real PyTorch transformer language model.

Components
----------
* ``TransformerBlock``      – Pre-LayerNorm block with GQA + FFN / MoE.
* ``GroupedQueryAttention`` – Multi-head attention where K/V use fewer
  heads than Q (GQA).
* ``build_rotary_pos_emb`` – Pre-compute cos / sin tables for RoPE.
* ``apply_rotary_pos_emb``  – Apply RoPE to query / key tensors.
* ``SwiGLU``                – Swish-gated linear unit activation.
* ``FeedForward``           – Dense SwiGLU FFN.
* ``MoELayer``              – Mixture-of-experts with top-k routing +
  load-balancing auxiliary loss.
* ``AstroVoxModel``         – Full LM: embeddings -> transformer blocks ->
  LM head producing logits.
* ``create_model``          – Factory callable accepting a config dict.

Author: AstroVoxAi
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Rotary Position Embedding (RoPE)
# ---------------------------------------------------------------------------


def _rope_inverse_freq(dim: int, base: float, device: torch.device) -> torch.Tensor:
    """Return ``[1/base^(0/dim), 1/base^(2/dim), ...]`` of shape *(dim/2,)*."""
    indices = torch.arange(0, dim, 2, device=device, dtype=torch.float32)
    return 1.0 / (base ** (indices / dim))


def build_rotary_pos_emb(
    seq_len: int,
    dim: int,
    base: float = 10000.0,
    device: torch.device = torch.device("cpu"),
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Pre-compute ``cos``/``sin`` rotation tables for RoPE.

    Returns two tensors of shape ``(1, seq_len, 1, dim)`` so they broadcast
    across the head dimension during multi-head attention.
    """
    inv_freq = _rope_inverse_freq(dim, base, device)                         # (dim/2,)
    positions = torch.arange(seq_len, device=device, dtype=torch.float32)    # (seq_len,)
    freqs = positions[:, None] * inv_freq[None, :]                            # (seq_len, dim/2)
    # Interleave to match the standard RoPE convention
    emb = torch.cat([freqs, freqs], dim=-1)                                  # (seq_len, dim)
    cos = emb.cos().unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, dim)
    sin = emb.sin().unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, dim)
    return cos, sin


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    """Apply the 90-degree rotation ``[-x2, x1]`` used by RoPE."""
    x1, x2 = x[..., : x.shape[-1] // 2], x[..., x.shape[-1] // 2:]
    return torch.cat((-x2, x1), dim=-1)


def apply_rotary_pos_emb(
    q: torch.Tensor,
    k: torch.Tensor,
    cos: torch.Tensor,
    sin: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Rotate query and key tensors using pre-computed ``cos`` / ``sin``.

    Args:
        q: ``(batch, n_heads, seq_len, head_dim)``
        k: ``(batch, n_kv_heads, seq_len, head_dim)``
        cos: ``(1, seq_len, 1, head_dim)``
        sin: ``(1, seq_len, 1, head_dim)``

    Returns:
        ``(q_rot, k_rot)`` with the same shapes as the inputs.
    """
    q_rot = (q * cos) + (rotate_half(q) * sin)
    k_rot = (k * cos) + (rotate_half(k) * sin)
    return q_rot, k_rot


# ---------------------------------------------------------------------------
# Grouped-Query Attention (GQA)
# ---------------------------------------------------------------------------


class GroupedQueryAttention(nn.Module):
    """Multi-head attention where keys and values use fewer heads than queries.

    When ``n_kv_heads < n_heads`` the key/value pairs are shared across
    ``n_heads // n_kv_heads`` consecutive query heads, which reduces the
    KV-cache memory footprint by the same factor while preserving
    competitive perplexity (as in *Grouped-Query Attention*).
    """

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        n_kv_heads: Optional[int] = None,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads or n_heads
        assert n_heads % self.n_kv_heads == 0, "n_heads must be divisible by n_kv_heads"
        self.n_groups = n_heads // self.n_kv_heads
        self.head_dim = d_model // n_heads

        # QKV projection layers
        self.q_proj = nn.Linear(d_model, n_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(d_model, self.n_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(d_model, self.n_kv_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(n_heads * self.head_dim, d_model, bias=False)

        self.attn_dropout = nn.Dropout(dropout)
        self.resid_dropout = nn.Dropout(dropout)

    def _repeat_kv(self, kv: torch.Tensor) -> torch.Tensor:
        """Repeat K/V heads so the number of heads matches the query count."""
        bsz, n_kv, slen, hd = kv.shape
        if self.n_groups == 1:
            return kv
        # Insert a new axis, expand, then flatten: (bsz, n_kv * n_groups, slen, hd)
        return (
            kv[:, :, None, :, :]
            .expand(bsz, n_kv, self.n_groups, slen, hd)
            .reshape(bsz, n_kv * self.n_groups, slen, hd)
        )

    def forward(
        self,
        x: torch.Tensor,
        cos: Optional[torch.Tensor] = None,
        sin: Optional[torch.Tensor] = None,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Args:
            x:       ``(batch, seq_len, d_model)``
            cos/sin: RoPE tables of shape ``(1, seq_len, 1, head_dim)``
            mask:    Additive attention mask ``(batch, 1, seq_len, seq_len)``
        """
        bsz, slen, _ = x.shape

        q = self.q_proj(x).view(bsz, slen, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(bsz, slen, self.n_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(bsz, slen, self.n_kv_heads, self.head_dim).transpose(1, 2)

        # Apply rotary position embedding to Q and K
        if cos is not None and sin is not None:
            q, k = apply_rotary_pos_emb(q, k, cos, sin)

        # Share K/V across query heads (GQA expansion)
        k = self._repeat_kv(k)
        v = self._repeat_kv(v)

        # Scaled dot-product attention
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        if mask is not None:
            scores = scores + mask
        attn = F.softmax(scores.float(), dim=-1).to(scores.dtype)
        attn = self.attn_dropout(attn)

        out = torch.matmul(attn, v)                                  # (bsz, n_heads, slen, head_dim)
        out = out.transpose(1, 2).contiguous().view(bsz, slen, self.d_model)
        return self.resid_dropout(self.o_proj(out))


# ---------------------------------------------------------------------------
# SwiGLU activation
# ---------------------------------------------------------------------------


class SwiGLU(nn.Module):
    """Swish-Gated Linear Unit.

    Splits the input along the feature axis into ``(gate, value)`` then
    returns ``SiLU(gate) * value``.  The upstream linear layer must
    therefore produce ``2 * d_ff`` features.
    """

    def __init__(self) -> None:
        super().__init__()
        self.act = nn.SiLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gate, value = x.chunk(2, dim=-1)
        return self.act(gate) * value


# ---------------------------------------------------------------------------
# Dense feed-forward (used when MoE is disabled)
# ---------------------------------------------------------------------------


class FeedForward(nn.Module):
    """Two-layer FFN with SwiGLU activation and dropout."""

    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.0) -> None:
        super().__init__()
        self.fc1 = nn.Linear(d_model, d_ff * 2, bias=False)
        self.act = SwiGLU()
        self.fc2 = nn.Linear(d_ff, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.fc2(self.act(self.fc1(x))))


# ---------------------------------------------------------------------------
# Mixture-of-Experts (MoE)
# ---------------------------------------------------------------------------


class MoELayer(nn.Module):
    """Sparse MoE feed-forward layer with top-k routing.

    A linear router assigns each token to its top-``k`` experts.  Each
    expert is an independent SwiGLU FFN whose output is weighted by the
    corresponding routing probability and summed.

    An auxiliary *load-balancing loss* is returned alongside the output so
    the caller can add it to the main language-modeling loss (typically
    with a coefficient such as ``0.01``).  The loss follows the
    formulation in *Switch Transformers* (Fedus et al., 2021).
    """

    def __init__(
        self,
        d_model: int,
        d_ff: int,
        n_experts: int,
        top_k: int = 2,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        assert top_k <= n_experts, "top_k must not exceed n_experts"
        self.d_model = d_model
        self.d_ff = d_ff
        self.n_experts = n_experts
        self.top_k = top_k

        # Each expert is a self-contained SwiGLU FFN
        self.experts = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(d_model, d_ff * 2, bias=False),
                    SwiGLU(),
                    nn.Linear(d_ff, d_model, bias=False),
                    nn.Dropout(dropout),
                )
                for _ in range(n_experts)
            ]
        )
        # Router produces a logit per expert for every token
        self.router = nn.Linear(d_model, n_experts, bias=False)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: ``(batch, seq_len, d_model)``

        Returns:
            ``(output, aux_loss)`` where *output* has the same shape as *x*
            and *aux_loss* is a scalar tensor for load balancing.
        """
        *batch_shape, _ = x.shape
        flat = x.reshape(-1, self.d_model)  # (N, d_model)
        n_tokens = flat.shape[0]

        # Router probabilities (softmax over experts)
        probs = F.softmax(self.router(flat), dim=-1)  # (N, n_experts)
        topk_weights, topk_indices = torch.topk(probs, self.top_k, dim=-1)  # (N, k)

        # ---- load-balancing auxiliary loss (Switch-Transformer eq. 3) ----
        one_hot = F.one_hot(topk_indices, num_classes=self.n_experts).float()  # (N, k, E)
        expert_counts = one_hot.sum(dim=0)  # (k, E)
        mean_probs = probs.mean(dim=0)  # (E,)
        mean_counts = expert_counts.sum(dim=0) / n_tokens  # (E,)
        aux_loss = self.n_experts * (mean_probs * mean_counts).sum()

        # ---- dispatch tokens to their selected experts ----
        out = torch.zeros_like(flat)
        for exp_idx in range(self.n_experts):
            sel = topk_indices == exp_idx  # (N, k)
            rows, ks = sel.nonzero(as_tuple=True)
            if rows.numel() == 0:
                continue
            expert_out = self.experts[exp_idx](flat[rows])
            w = topk_weights[rows, ks].unsqueeze(-1)  # (M, 1)
            out[rows] += expert_out * w

        out = out.reshape(*batch_shape, self.d_model)
        self._aux_loss = aux_loss
        return out, aux_loss

    @property
    def load_balance_loss(self) -> torch.Tensor:
        """Return the last computed MoE load-balancing auxiliary loss."""
        return self._aux_loss if hasattr(self, "_aux_loss") else torch.tensor(0.0)


# ---------------------------------------------------------------------------
# Transformer block (Pre-LayerNorm)
# ---------------------------------------------------------------------------


class TransformerBlock(nn.Module):
    """Pre-LayerNorm transformer decoder block.

    Pre-LN applies ``LayerNorm`` *before* each sub-layer with a residual
    connection around it::

        h = x + SubLayer(LayerNorm(x))

    This stabilises training at depth compared to Post-LN.
    """

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        n_kv_heads: Optional[int] = None,
        d_ff: Optional[int] = None,
        dropout: float = 0.0,
        use_moe: bool = False,
        n_experts: int = 8,
        moe_top_k: int = 2,
        rope_base: float = 10000.0,
    ) -> None:
        super().__init__()
        d_ff = d_ff or d_model * 4

        # Self-attention sub-layer
        self.attention = GroupedQueryAttention(d_model, n_heads, n_kv_heads, dropout)
        self.attn_norm = nn.LayerNorm(d_model)

        # FFN sub-layer (either dense or MoE)
        if use_moe:
            self.ffn: nn.Module = MoELayer(d_model, d_ff, n_experts, moe_top_k, dropout)
            self.is_moe = True
        else:
            self.ffn = FeedForward(d_model, d_ff, dropout)
            self.is_moe = False
        self.ffn_norm = nn.LayerNorm(d_model)

        # RoPE configuration
        self.head_dim = self.attention.head_dim
        self.rope_base = rope_base
        self._rope_cache: Dict[int, Tuple[torch.Tensor, torch.Tensor]] = {}

    def _get_rope(
        self, seq_len: int, device: torch.device, dtype: torch.dtype
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Lazily compute and cache RoPE cos/sin tables for a given seq length."""
        if seq_len not in self._rope_cache:
            cos, sin = build_rotary_pos_emb(seq_len, self.head_dim, self.rope_base, device)
            self._rope_cache[seq_len] = (cos.to(dtype), sin.to(dtype))
        return self._rope_cache[seq_len]

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Args:
            x:    ``(batch, seq_len, d_model)``
            mask: Additive attention mask broadcastable to
                  ``(batch, n_heads, seq_len, seq_len)``

        Returns:
            ``(hidden, aux_loss)`` where *aux_loss* is the MoE
            load-balancing loss (or ``None`` for dense FFN).
        """
        cos, sin = self._get_rope(x.shape[1], x.device, x.dtype)

        # Attention sub-layer (Pre-LN + residual)
        h = x + self.attention(self.attn_norm(x), cos, sin, mask)

        # FFN sub-layer (Pre-LN + residual)
        if self.is_moe:
            ffn_out, aux_loss = self.ffn(self.ffn_norm(h))
            h = h + ffn_out
            return h, aux_loss

        h = h + self.ffn(self.ffn_norm(h))
        return h, None


# ---------------------------------------------------------------------------
# AstroVoxModel -- full language model
# ---------------------------------------------------------------------------


class AstroVoxModel(nn.Module):
    """Complete transformer decoder language model.

    Architecture::

        token + position embeddings -> dropout
        -> [TransformerBlock x n_layers]
        -> final LayerNorm -> LM head (logits)
    """

    def __init__(
        self,
        vocab_size: int = 32000,
        d_model: int = 4096,
        n_heads: int = 32,
        n_layers: int = 32,
        n_kv_heads: Optional[int] = None,
        max_seq_len: int = 2048,
        d_ff: Optional[int] = None,
        dropout: float = 0.0,
        use_moe: bool = False,
        n_experts: int = 8,
        moe_top_k: int = 2,
        rope_base: float = 10000.0,
        tie_weights: bool = True,
    ) -> None:
        super().__init__()
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.max_seq_len = max_seq_len
        self.use_moe = use_moe

        # Token and positional embeddings
        self.tok_embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq_len, d_model)
        self.embed_dropout = nn.Dropout(dropout)

        # Transformer block stack
        self.blocks = nn.ModuleList(
            [
                TransformerBlock(
                    d_model=d_model,
                    n_heads=n_heads,
                    n_kv_heads=n_kv_heads,
                    d_ff=d_ff,
                    dropout=dropout,
                    use_moe=use_moe,
                    n_experts=n_experts,
                    moe_top_k=moe_top_k,
                    rope_base=rope_base,
                )
                for _ in range(n_layers)
            ]
        )

        # Final processing
        self.norm = nn.LayerNorm(d_model)
        self.lm_head = nn.Linear(d_model, vocab_size, bias=False)

        # Weight tying: output projection shares the embedding matrix
        if tie_weights:
            self.lm_head.weight = self.tok_embed.weight

        self._aux_loss: Optional[torch.Tensor] = None
        self.apply(self._init_weights)

    # -- weight initialisation -------------------------------------------

    def _init_weights(self, module: nn.Module) -> None:
        """Initialise weights with a small normal distribution (std=0.02)."""
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    # -- attention masks -------------------------------------------------

    @staticmethod
    def _build_causal_mask(
        seq_len: int, device: torch.device, dtype: torch.dtype
    ) -> torch.Tensor:
        """Additive causal mask of shape ``(1, 1, seq_len, seq_len)``.

        Positions in the lower triangle (including diagonal) are 0
        (attend) and positions in the strict upper triangle are
        ``-inf`` (masked).
        """
        mask = torch.full((seq_len, seq_len), float("-inf"), device=device, dtype=dtype)
        mask = torch.triu(mask, diagonal=1)
        return mask.unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, seq_len)

    @staticmethod
    def _build_padding_mask(
        attention_mask: torch.Tensor, seq_len: int, dtype: torch.dtype
    ) -> torch.Tensor:
        """Convert a padding mask to additive form.

        Args:
            attention_mask: ``(batch, seq_len)`` where 1 = real token,
                            0 = padding.
            seq_len:        Sequence length (== ``attention_mask.shape[1]``).

        Returns:
            ``(batch, 1, seq_len, seq_len)`` additive mask (broadcastable
            over heads); padding key positions are ``-inf``.
        """
        bsz = attention_mask.shape[0]
        pad = attention_mask == 0  # (bsz, seq_len)  -- True where padding
        pad = pad.view(bsz, 1, 1, seq_len)  # (bsz, 1, 1, seq_len)
        pad = pad.expand(bsz, 1, seq_len, seq_len)  # (bsz, 1, seq_len, seq_len)
        return pad.to(dtype=dtype).mul(float("-inf"))

    # -- forward ---------------------------------------------------------

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Run a forward pass and return logits.

        Args:
            input_ids:      ``(batch, seq_len)`` token IDs.
            attention_mask: ``(batch, seq_len)`` with 1 for real tokens
                            and 0 for padding.  When ``None`` a plain
                            causal mask is used.

        Returns:
            Logits of shape ``(batch, seq_len, vocab_size)``.
        """
        bsz, seq_len = input_ids.shape
        if seq_len > self.max_seq_len:
            raise ValueError(
                f"Sequence length {seq_len} exceeds max_seq_len {self.max_seq_len}"
            )

        # Embedding lookup
        positions = torch.arange(seq_len, device=input_ids.device)
        x = self.tok_embed(input_ids) + self.pos_embed(positions)
        x = self.embed_dropout(x)

        # Combine causal mask with optional padding mask
        attn_mask = self._build_causal_mask(seq_len, input_ids.device, x.dtype)  # (1, 1, s, s)
        if attention_mask is not None:
            pad_mask = self._build_padding_mask(attention_mask, seq_len, x.dtype)  # (bsz, 1, s, s)
            attn_mask = attn_mask + pad_mask  # broadcasts to (bsz, 1, s, s)

        # Transformer blocks
        aux_losses: List[torch.Tensor] = []
        for block in self.blocks:
            x, aux = block(x, mask=attn_mask)
            if aux is not None:
                aux_losses.append(aux)

        # Final projection
        x = self.norm(x)
        logits = self.lm_head(x)

        # Stash MoE auxiliary loss for later retrieval
        self._aux_loss = torch.stack(aux_losses).mean() if aux_losses else None
        return logits

    # -- properties ------------------------------------------------------

    @property
    def aux_loss(self) -> Optional[torch.Tensor]:
        """Return the mean MoE load-balancing loss (valid after ``forward``).

        When using MoE, add ``model(aux_loss) * 0.01`` (or your preferred
        coefficient) to the main language-modeling loss during training.
        """
        return self._aux_loss

    @property
    def n_params(self) -> int:
        """Return the total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: Dict[str, Any] = {
    "vocab_size": 32000,
    "d_model": 4096,
    "n_heads": 32,
    "n_layers": 32,
    "n_kv_heads": None,       # falls back to n_heads (standard multi-head attention)
    "max_seq_len": 2048,
    "d_ff": None,             # falls back to d_model * 4
    "dropout": 0.0,
    "use_moe": False,
    "n_experts": 8,
    "moe_top_k": 2,
    "rope_base": 10000.0,
    "tie_weights": True,
}


def create_model(config: Optional[Dict[str, Any]] = None) -> AstroVoxModel:
    """Create an :class:`AstroVoxModel` from a config dictionary.

    Any keys present in *config* override the defaults in
    :data:`DEFAULT_CONFIG`.

    Example::

        model = create_model({
            "vocab_size": 32000,
            "d_model": 2048,
            "n_heads": 16,
            "n_kv_heads": 4,
            "n_layers": 16,
            "max_seq_len": 2048,
            "use_moe": True,
            "n_experts": 8,
            "moe_top_k": 2,
            "dropout": 0.1,
        })
        logits = model(input_ids)
        loss = F.cross_entropy(logits[..., :-1, :], targets[..., 1:, :])
        loss = loss + 0.01 * model.aux_loss
    """
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    return AstroVoxModel(**cfg)
