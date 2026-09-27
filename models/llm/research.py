from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# 1. Mixture of Experts (MoE)
# ---------------------------------------------------------------------------


class Expert(nn.Module):
    """Single expert network with SwiGLU-style feedforward activation."""

    def __init__(
        self,
        hidden_size: int,
        intermediate_size: int,
        dropout: float = 0.0,
        bias: bool = False,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.gate_proj = nn.Linear(
            hidden_size, intermediate_size, bias=bias, device=device, dtype=dtype
        )
        self.up_proj = nn.Linear(
            hidden_size, intermediate_size, bias=bias, device=device, dtype=dtype
        )
        self.down_proj = nn.Linear(
            intermediate_size, hidden_size, bias=bias, device=device, dtype=dtype
        )
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        return self.dropout(
            self.down_proj(self.act(self.gate_proj(hidden_states)) * self.up_proj(hidden_states))
        )


class TopKRouter(nn.Module):
    """Top-k token routing with expert-level load balancing."""

    def __init__(self, hidden_size: int, num_experts: int, top_k: int = 2):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = top_k
        self.gate = nn.Linear(hidden_size, num_experts, bias=False)

    def forward(
        self, hidden_states: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        logits = self.gate(hidden_states)
        scores = F.softmax(logits, dim=-1, dtype=torch.float32)
        topk_scores, topk_indices = torch.topk(scores, self.top_k, dim=-1)
        topk_scores = topk_scores / topk_scores.sum(dim=-1, keepdim=True)
        return topk_indices, topk_scores.to(hidden_states.dtype), logits


def load_balancing_loss(
    gate_logits: torch.Tensor, topk_indices: torch.Tensor, num_experts: int
) -> torch.Tensor:
    """Auxiliary load-balancing loss to encourage even expert utilization."""
    probs = F.softmax(gate_logits, dim=-1)
    token_expert_fraction = torch.zeros(gate_logits.size(0), num_experts, device=gate_logits.device)
    token_expert_fraction.scatter_add_(1, topk_indices, probs)
    mean_probs = token_expert_fraction.mean(dim=0)
    expert_util = token_expert_fraction.mean(dim=0)
    return num_experts * 0.5 * (expert_util * mean_probs).sum()


class MoELayer(nn.Module):
    """Mixture-of-Experts feedforward layer with top-k routing."""

    def __init__(
        self,
        hidden_size: int,
        intermediate_size: int,
        num_experts: int = 8,
        top_k: int = 2,
        dropout: float = 0.0,
        bias: bool = False,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.num_experts = num_experts
        self.top_k = top_k
        self.experts = nn.ModuleList(
            [
                Expert(
                    hidden_size,
                    intermediate_size,
                    dropout=dropout,
                    bias=bias,
                    device=device,
                    dtype=dtype,
                )
                for _ in range(num_experts)
            ]
        )
        self.router = TopKRouter(hidden_size, num_experts, top_k=top_k)

    def forward(self, hidden_states: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        B, T, C = hidden_states.shape
        flat = hidden_states.view(-1, C)
        topk_indices, topk_scores, gate_logits = self.router(flat)
        out = torch.zeros_like(flat)
        for i in range(self.top_k):
            expert_indices = topk_indices[:, i]
            expert_scores = topk_scores[:, i]
            for expert_idx in range(self.num_experts):
                mask = expert_indices == expert_idx
                if mask.any():
                    out[mask] += expert_scores[mask].unsqueeze(-1) * self.experts[expert_idx](
                        flat[mask]
                    )
        lb_loss = load_balancing_loss(gate_logits, topk_indices, self.num_experts)
        return out.view(B, T, C), lb_loss


# ---------------------------------------------------------------------------
# 2. State Space Models (SSM)
# ---------------------------------------------------------------------------


class S4Kernel(nn.Module):
    """Simplified S4 (Structured State Space) kernel with HiPPO initialization."""

    def __init__(
        self, d_state: int = 16, d_model: int = 768, dt_min: float = 0.001, dt_max: float = 0.1
    ):
        super().__init__()
        self.d_state = d_state
        self.d_model = d_model
        self.A = nn.Parameter(torch.randn(d_model, d_state))
        self.B = nn.Parameter(torch.randn(d_model, d_state))
        self.C = nn.Parameter(torch.randn(d_model, d_state))
        log_dt = torch.rand(d_model) * (math.log(dt_max) - math.log(dt_min)) + math.log(dt_min)
        self.log_dt = nn.Parameter(log_dt)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.A, mean=0.0, std=0.02)
        nn.init.normal_(self.B, mean=0.0, std=0.02)
        nn.init.normal_(self.C, mean=0.0, std=0.02)

    def forward(self, u: torch.Tensor) -> torch.Tensor:
        dt = torch.exp(self.log_dt).to(u.dtype)
        A = self.A.to(u.dtype)
        B = self.B.to(u.dtype)
        C = self.C.to(u.dtype)
        dA = torch.exp(torch.einsum("bd,dn->bn", dt, A))
        dB = torch.einsum("bd,dn->bn", dt, B)
        x = torch.zeros(u.size(0), self.d_model, self.d_state, device=u.device, dtype=u.dtype)
        ys = []
        for t in range(u.size(1)):
            x = dA * x + dB * u[:, t].unsqueeze(-1)
            y = torch.einsum("bdn,dn->bd", x, C)
            ys.append(y.unsqueeze(1))
        return torch.cat(ys, dim=1)


class MambaBlock(nn.Module):
    """Mamba-style selective state-space block with input-dependent parameters."""

    def __init__(
        self,
        d_model: int = 768,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        dt_rank: int = 16,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.d_model = d_model
        self.d_inner = expand * d_model
        self.d_state = d_state
        self.d_conv = d_conv
        self.dt_rank = dt_rank
        self.in_proj = nn.Linear(d_model, self.d_inner * 2, bias=False, device=device, dtype=dtype)
        self.conv1d = nn.Conv1d(
            self.d_inner,
            self.d_inner,
            d_conv,
            groups=self.d_inner,
            padding=d_conv - 1,
            device=device,
            dtype=dtype,
        )
        self.act = nn.SiLU()
        self.x_proj = nn.Linear(
            self.d_inner, dt_rank + d_state * 2, bias=False, device=device, dtype=dtype
        )
        self.dt_proj = nn.Linear(dt_rank, self.d_inner, bias=True, device=device, dtype=dtype)
        self.A_log = nn.Parameter(torch.randn(self.d_inner, d_state))
        self.D = nn.Parameter(torch.randn(self.d_inner))
        self.out_proj = nn.Linear(self.d_inner, d_model, bias=False, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.A_log, mean=0.0, std=0.02)
        nn.init.normal_(self.D, mean=0.0, std=0.02)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        B, L, D = hidden_states.shape
        x_and_z = self.in_proj(hidden_states)
        x, z = x_and_z.chunk(2, dim=-1)
        x = x.transpose(1, 2)
        x = self.conv1d(x)[:, :, :L]
        x = x.transpose(1, 2)
        x = self.act(x)
        A = -torch.exp(self.A_log.float()).to(x.dtype)
        delta = self.dt_proj(self.x_proj(x)).transpose(1, 2)
        delta = F.softplus(delta)
        y = self._ssm(x, delta, A)
        y = y * self.act(z)
        return self.out_proj(y)

    def _ssm(self, x: torch.Tensor, delta: torch.Tensor, A: torch.Tensor) -> torch.Tensor:
        B_ssm, L, D = x.shape
        N = A.size(1)
        A = A.unsqueeze(0).unsqueeze(0)
        deltaA = torch.exp(torch.einsum("bld,dn->bln", delta, A.squeeze(0)))
        deltaB = delta.unsqueeze(-1) * 1.0
        x_proj = x.unsqueeze(-1)
        y = torch.zeros_like(x)
        h = torch.zeros(B_ssm, D, N, device=x.device, dtype=x.dtype)
        for t in range(L):
            h = deltaA[:, t] * h + deltaB[:, t] * x_proj[:, t]
            y[:, t] = torch.einsum(
                "bdn,dn->bd", h, torch.ones(D, N, device=x.device, dtype=x.dtype)
            )
        return y


class HybridTransformerSSM(nn.Module):
    """Interleave transformer attention blocks with SSM blocks for hybrid reasoning."""

    def __init__(
        self,
        d_model: int = 768,
        num_heads: int = 12,
        d_state: int = 16,
        expand: int = 2,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.attn = nn.MultiheadAttention(
            d_model, num_heads, batch_first=True, device=device, dtype=dtype
        )
        self.ln1 = nn.LayerNorm(d_model, device=device, dtype=dtype)
        self.ln2 = nn.LayerNorm(d_model, device=device, dtype=dtype)
        self.ssm = MambaBlock(
            d_model=d_model, d_state=d_state, expand=expand, device=device, dtype=dtype
        )

    def forward(self, x: torch.Tensor, attention_mask: torch.Tensor | None = None) -> torch.Tensor:
        attn_out, _ = self.attn(
            self.ln1(x), self.ln1(x), self.ln1(x), key_padding_mask=attention_mask
        )
        x = x + attn_out
        x = x + self.ssm(self.ln2(x))
        return x


# ---------------------------------------------------------------------------
# 3. Long-Context Methods
# ---------------------------------------------------------------------------


class AliBiMultiHeadAttention(nn.Module):
    """Attention with Attention with Linear Biases (ALiBi) for extrapolation."""

    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        max_position_embeddings: int = 2048,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        if hidden_size % num_attention_heads != 0:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        self.num_attention_heads = num_attention_heads
        self.head_dim = hidden_size // num_attention_heads
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.relative_bias = nn.Parameter(torch.zeros(num_attention_heads, max_position_embeddings))
        self.dropout = nn.Dropout(dropout)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.relative_bias, mean=0.0, std=0.02)

    def forward(
        self, hidden_states: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        q = (
            self.q_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        k = (
            self.k_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        v = (
            self.v_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        scale = self.head_dim**-0.5
        attn = torch.matmul(q, k.transpose(-2, -1)) * scale
        seq_range = torch.arange(T, device=hidden_states.device)
        bias = self.relative_bias[:, seq_range]
        attn = attn + bias.unsqueeze(0).unsqueeze(2)
        if attention_mask is not None:
            attn = attn + attention_mask
        attn = F.softmax(attn, dim=-1, dtype=torch.float32).to(hidden_states.dtype)
        attn = self.dropout(attn)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


class YaRNExtendedRotaryEmbedding(nn.Module):
    """YaRN-enhanced RoPE scaling for long-context extrapolation."""

    def __init__(
        self,
        dim: int,
        max_position_embeddings: int = 2048,
        base: float = 10000.0,
        scale: float = 1.0,
        device=None,
    ):
        super().__init__()
        self.dim = dim
        self.max_position_embeddings = max_position_embeddings
        self.base = base
        self.scale = scale
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float().to(device) / dim)) * scale
        self.register_buffer("inv_freq", inv_freq, persistent=False)
        self.max_seq_len_cached = 0
        self.cos_cached = None
        self.sin_cached = None

    def _set_cos_sin_cache(self, seq_len: int, device=None, dtype=None):
        if (
            seq_len == self.max_seq_len_cached
            and self.cos_cached is not None
            and self.sin_cached is not None
        ):
            if device is not None:
                self.cos_cached = self.cos_cached.to(device)
                self.sin_cached = self.sin_cached.to(device)
            if dtype is not None:
                self.cos_cached = self.cos_cached.to(dtype)
                self.sin_cached = self.sin_cached.to(dtype)
            return
        self.max_seq_len_cached = seq_len
        t = torch.arange(self.max_seq_len_cached, device=device, dtype=self.inv_freq.dtype)
        freqs = torch.outer(t, self.inv_freq)
        emb = torch.cat((freqs, freqs), dim=-1)
        self.cos_cached = emb.cos().to(device).to(dtype)
        self.sin_cached = emb.sin().to(device).to(dtype)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        seq_len = x.size(1)
        self._set_cos_sin_cache(seq_len=seq_len, device=x.device, dtype=x.dtype)
        return self.cos_cached[:seq_len].unsqueeze(0).unsqueeze(0), self.sin_cached[
            :seq_len
        ].unsqueeze(0).unsqueeze(0)


class WindowedAttention(nn.Module):
    """Windowed local attention for long-sequence efficiency."""

    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        window_size: int = 512,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        if hidden_size % num_attention_heads != 0:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        self.num_attention_heads = num_attention_heads
        self.head_dim = hidden_size // num_attention_heads
        self.window_size = window_size
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.dropout = nn.Dropout(dropout)
        self._reset_parameters()

    def _reset_parameters(self):
        for proj in [self.q_proj, self.k_proj, self.v_proj, self.o_proj]:
            nn.init.normal_(proj.weight, mean=0.0, std=0.02)

    def forward(
        self, hidden_states: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        q = (
            self.q_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        k = (
            self.k_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        v = (
            self.v_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        scale = self.head_dim**-0.5
        half_win = self.window_size // 2
        outputs = []
        for start in range(0, T, self.window_size):
            end = min(start + self.window_size, T)
            q_w = q[:, :, start:end, :]
            k_w = k[:, :, max(0, start - half_win) : min(T, end + half_win), :]
            v_w = v[:, :, max(0, start - half_win) : min(T, end + half_win), :]
            attn = torch.matmul(q_w, k_w.transpose(-2, -1)) * scale
            if attention_mask is not None:
                mask = attention_mask[
                    :, :, start:end, max(0, start - half_win) : min(T, end + half_win)
                ]
                attn = attn + mask
            attn = F.softmax(attn, dim=-1, dtype=torch.float32).to(hidden_states.dtype)
            attn = self.dropout(attn)
            out = torch.matmul(attn, v_w).transpose(1, 2).contiguous().view(end - start, C)
            outputs.append(out)
        return torch.cat(outputs, dim=0).unsqueeze(0)


# ---------------------------------------------------------------------------
# 4. Retrieval-Augmented Generation (RAG)
# ---------------------------------------------------------------------------


class Document:
    """Simple document container for retrieval."""

    def __init__(
        self,
        doc_id: str,
        text: str,
        embedding: torch.Tensor | None = None,
        metadata: dict | None = None,
    ):
        self.doc_id = doc_id
        self.text = text
        self.embedding = embedding
        self.metadata = metadata or {}


class DocumentStore:
    """Vector-backed document store with cosine retrieval."""

    def __init__(self, embedding_dim: int = 768, device: torch.device | None = None):
        self.documents: list[Document] = []
        self.index: torch.Tensor | None = None
        self.embedding_dim = embedding_dim
        self.device = device or torch.device("cpu")

    def add_documents(self, documents: list[Document]) -> None:
        for doc in documents:
            if doc.embedding is not None:
                doc.embedding = doc.embedding.to(self.device)
        self.documents.extend(documents)
        embeddings = [doc.embedding for doc in documents if doc.embedding is not None]
        if embeddings:
            new_index = torch.stack(embeddings, dim=0)
            self.index = (
                new_index if self.index is None else torch.cat([self.index, new_index], dim=0)
            )

    def query(self, query_embedding: torch.Tensor, top_k: int = 5) -> list[tuple[Document, float]]:
        if self.index is None or len(self.documents) == 0:
            return []
        query_embedding = query_embedding.to(self.device)
        query_embedding = query_embedding / (query_embedding.norm(dim=-1, keepdim=True) + 1e-8)
        index = self.index / (self.index.norm(dim=-1, keepdim=True) + 1e-8)
        scores = torch.matmul(index, query_embedding.unsqueeze(-1)).squeeze(-1)
        top_scores, top_indices = torch.topk(scores, min(top_k, scores.size(0)))
        results = []
        for score, idx in zip(top_scores.tolist(), top_indices.tolist(), strict=False):
            results.append((self.documents[idx], float(score)))
        return results


class Retriever(nn.Module):
    """Neural retriever that encodes queries and documents."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_layers: int = 4,
        max_seq_len: int = 512,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size, nhead=8, batch_first=True, device=device, dtype=dtype
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.max_seq_len = max_seq_len

    def forward(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        x = self.embedding(input_ids)
        x = self.encoder(x, src_key_padding_mask=attention_mask)
        x = x.transpose(1, 2)
        pooled = self.pool(x).squeeze(-1)
        return pooled


class RAGGenerator(nn.Module):
    """RAG generator that augments input with retrieved documents."""

    def __init__(
        self,
        vocab_size: int = 32000,
        hidden_size: int = 768,
        num_layers: int = 6,
        num_heads: int = 12,
        max_context_docs: int = 3,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size, device=device, dtype=dtype)
        self.num_context_docs = max_context_docs
        self.cross_attn = nn.MultiheadAttention(
            hidden_size, num_heads, batch_first=True, device=device, dtype=dtype
        )
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=hidden_size, nhead=num_heads, batch_first=True, device=device, dtype=dtype
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=num_layers)
        self.lm_head = nn.Linear(hidden_size, vocab_size, bias=False, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.embedding.weight, mean=0.0, std=0.02)
        nn.init.normal_(self.lm_head.weight, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        retrieved_embeddings: torch.Tensor | None = None,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        x = self.embedding(input_ids)
        if retrieved_embeddings is not None:
            memory, _ = self.cross_attn(x, retrieved_embeddings, retrieved_embeddings)
            x = x + memory
        x = self.decoder(x, x)
        return self.lm_head(x)


# ---------------------------------------------------------------------------
# 5. Memory-Augmented Transformers
# ---------------------------------------------------------------------------


class ExternalMemory(nn.Module):
    """External key-value memory bank with read/write operations."""

    def __init__(
        self,
        memory_size: int = 1024,
        hidden_size: int = 768,
        num_heads: int = 8,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.memory_size = memory_size
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.memory_key = nn.Parameter(
            torch.randn(memory_size, hidden_size, device=device, dtype=dtype)
        )
        self.memory_value = nn.Parameter(
            torch.randn(memory_size, hidden_size, device=device, dtype=dtype)
        )
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.memory_key, mean=0.0, std=0.02)
        nn.init.normal_(self.memory_value, mean=0.0, std=0.02)

    def read(self, hidden_states: torch.Tensor) -> torch.Tensor:
        B, T, C = hidden_states.shape
        q = self.q_proj(hidden_states).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(self.memory_key).unsqueeze(0).transpose(1, 2)
        v = self.v_proj(self.memory_value).unsqueeze(0).transpose(1, 2)
        scale = self.head_dim**-0.5
        attn = torch.matmul(q, k) * scale
        attn = F.softmax(attn, dim=-1, dtype=torch.float32).to(hidden_states.dtype)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)

    def write(self, hidden_states: torch.Tensor) -> None:
        with torch.no_grad():
            update = hidden_states.mean(dim=(0, 1), keepdim=True)
            self.memory_key.data = 0.99 * self.memory_key.data + 0.01 * update
            self.memory_value.data = 0.99 * self.memory_value.data + 0.01 * update


class CompressiveMemory(nn.Module):
    """Compressive memory that compresses older tokens into summary states."""

    def __init__(self, hidden_size: int = 768, compression_ratio: int = 4, device=None, dtype=None):
        super().__init__()
        self.compression_ratio = compression_ratio
        self.compress = nn.Linear(
            hidden_size * compression_ratio, hidden_size, bias=False, device=device, dtype=dtype
        )
        self.expand = nn.Linear(
            hidden_size, hidden_size * compression_ratio, bias=False, device=device, dtype=dtype
        )
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.compress.weight, mean=0.0, std=0.02)
        nn.init.normal_(self.expand.weight, mean=0.0, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        if self.compression_ratio > T:
            return x
        pad = (self.compression_ratio - T % self.compression_ratio) % self.compression_ratio
        if pad > 0:
            x = F.pad(x, (0, 0, 0, pad))
        grouped = x.view(B, -1, self.compression_ratio * C)
        compressed = self.compress(grouped)
        expanded = self.expand(compressed).view(B, -1, C)
        return expanded[:, :T, :]


class MemoryNetwork(nn.Module):
    """Memory-augmented network with external memory read/write interface."""

    def __init__(
        self,
        input_size: int = 768,
        hidden_size: int = 768,
        memory_size: int = 128,
        memory_dim: int = 768,
        num_layers: int = 4,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.embed = nn.Linear(input_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.layers = nn.ModuleList(
            [nn.LayerNorm(hidden_size, device=device, dtype=dtype) for _ in range(num_layers)]
        )
        self.memory_key = nn.Parameter(
            torch.randn(memory_size, memory_dim, device=device, dtype=dtype)
        )
        self.memory_value = nn.Parameter(
            torch.randn(memory_size, memory_dim, device=device, dtype=dtype)
        )
        self.q_proj = nn.Linear(hidden_size, memory_dim, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, memory_dim, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, memory_dim, bias=False, device=device, dtype=dtype)
        self.out_proj = nn.Linear(memory_dim, hidden_size, bias=False, device=device, dtype=dtype)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.memory_key, mean=0.0, std=0.02)
        nn.init.normal_(self.memory_value, mean=0.0, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.embed(x)
        for layer in self.layers:
            residual = x
            q = self.q_proj(x)
            k = self.k_proj(self.memory_key).unsqueeze(0)
            v = self.v_proj(self.memory_value).unsqueeze(0)
            attn = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(q.size(-1))
            attn = F.softmax(attn, dim=-1)
            x = self.out_proj(torch.matmul(attn, v))
            x = layer(x + residual)
        return x


# ---------------------------------------------------------------------------
# 6. Multimodal Architectures
# ---------------------------------------------------------------------------


class VisionEncoder(nn.Module):
    """Vision Transformer encoder for image tokens."""

    def __init__(
        self,
        image_size: int = 224,
        patch_size: int = 16,
        num_channels: int = 3,
        hidden_size: int = 768,
        num_layers: int = 12,
        num_heads: int = 12,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.patch_embed = nn.Conv2d(
            num_channels,
            hidden_size,
            kernel_size=patch_size,
            stride=patch_size,
            bias=True,
            device=device,
            dtype=dtype,
        )
        num_patches = (image_size // patch_size) ** 2
        self.pos_embed = nn.Parameter(
            torch.zeros(1, num_patches + 1, hidden_size, device=device, dtype=dtype)
        )
        self.cls_token = nn.Parameter(torch.zeros(1, 1, hidden_size, device=device, dtype=dtype))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size, nhead=num_heads, batch_first=True, device=device, dtype=dtype
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self._reset_parameters()

    def _reset_parameters(self):
        nn.init.normal_(self.pos_embed, mean=0.0, std=0.02)
        nn.init.normal_(self.cls_token, mean=0.0, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B = x.size(0)
        x = self.patch_embed(x).flatten(2).transpose(1, 2)
        cls_tokens = self.cls_token.expand(B, -1, -1)
        x = torch.cat([cls_tokens, x], dim=1) + self.pos_embed
        return self.encoder(x)


class AudioEncoder(nn.Module):
    """Audio encoder using convolutional frontend and transformer backbone."""

    def __init__(
        self,
        input_channels: int = 1,
        hidden_size: int = 768,
        num_layers: int = 8,
        num_heads: int = 12,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.conv_frontend = nn.Sequential(
            nn.Conv1d(
                input_channels,
                hidden_size,
                kernel_size=4,
                stride=2,
                padding=1,
                device=device,
                dtype=dtype,
            ),
            nn.ReLU(),
            nn.Conv1d(
                hidden_size,
                hidden_size,
                kernel_size=4,
                stride=2,
                padding=1,
                device=device,
                dtype=dtype,
            ),
            nn.ReLU(),
        )
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size, nhead=num_heads, batch_first=True, device=device, dtype=dtype
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv_frontend(x).transpose(1, 2)
        return self.encoder(x)


class CrossModalAttention(nn.Module):
    """Bidirectional cross-attention between two modalities."""

    def __init__(
        self, hidden_size: int, num_heads: int = 8, dropout: float = 0.0, device=None, dtype=None
    ):
        super().__init__()
        if hidden_size % num_heads != 0:
            raise ValueError("hidden_size must be divisible by num_heads")
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        query_states: torch.Tensor,
        key_value_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T, C = query_states.shape
        q = self.q_proj(query_states).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(key_value_states).view(B, -1, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(key_value_states).view(B, -1, self.num_heads, self.head_dim).transpose(1, 2)
        scale = self.head_dim**-0.5
        attn = torch.matmul(q, k.transpose(-2, -1)) * scale
        if attention_mask is not None:
            attn = attn + attention_mask
        attn = F.softmax(attn, dim=-1, dtype=torch.float32).to(query_states.dtype)
        attn = self.dropout(attn)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


# ---------------------------------------------------------------------------
# 7. Efficient Attention Variants
# ---------------------------------------------------------------------------


class LinearAttention(nn.Module):
    """Linear-time attention using kernel feature maps."""

    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        if hidden_size % num_attention_heads != 0:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        self.num_attention_heads = num_attention_heads
        self.head_dim = hidden_size // num_attention_heads
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.dropout = nn.Dropout(dropout)
        self.elu = nn.ELU()

    def forward(
        self, hidden_states: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        q = (
            self.q_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        k = (
            self.k_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        v = (
            self.v_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        q = self.elu(q) + 1.0
        k = self.elu(k) + 1.0
        kv = torch.matmul(k.transpose(-2, -1), v)
        z = 1.0 / (torch.einsum("bhd,bdh->bh", q, k.unsqueeze(1).transpose(-2, -1)) + 1e-8)
        out = torch.matmul(q, kv) * z.unsqueeze(-1)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


class MultiQueryAttention(nn.Module):
    """Multi-query attention with shared key/value heads."""

    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        num_kv_heads: int = 1,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        if hidden_size % num_attention_heads != 0:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        self.num_attention_heads = num_attention_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = hidden_size // num_attention_heads
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(
            hidden_size, num_kv_heads * self.head_dim, bias=False, device=device, dtype=dtype
        )
        self.v_proj = nn.Linear(
            hidden_size, num_kv_heads * self.head_dim, bias=False, device=device, dtype=dtype
        )
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self, hidden_states: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        q = (
            self.q_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        k = self.k_proj(hidden_states).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(hidden_states).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        k = k.repeat_interleave(self.num_attention_heads // self.num_kv_heads, dim=1)
        v = v.repeat_interleave(self.num_attention_heads // self.num_kv_heads, dim=1)
        scale = self.head_dim**-0.5
        attn = torch.matmul(q, k.transpose(-2, -1)) * scale
        if attention_mask is not None:
            attn = attn + attention_mask
        attn = F.softmax(attn, dim=-1, dtype=torch.float32).to(hidden_states.dtype)
        attn = self.dropout(attn)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


class GroupedQueryAttention(nn.Module):
    """Grouped-query attention with shared KV heads across groups of Q heads."""

    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        num_kv_heads: int = 4,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        if hidden_size % num_attention_heads != 0:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        self.num_attention_heads = num_attention_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = hidden_size // num_attention_heads
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(
            hidden_size, num_kv_heads * self.head_dim, bias=False, device=device, dtype=dtype
        )
        self.v_proj = nn.Linear(
            hidden_size, num_kv_heads * self.head_dim, bias=False, device=device, dtype=dtype
        )
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self, hidden_states: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        q = (
            self.q_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        k = self.k_proj(hidden_states).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(hidden_states).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        repeats = self.num_attention_heads // self.num_kv_heads
        k = k.repeat_interleave(repeats, dim=1)
        v = v.repeat_interleave(repeats, dim=1)
        scale = self.head_dim**-0.5
        attn = torch.matmul(q, k.transpose(-2, -1)) * scale
        if attention_mask is not None:
            attn = attn + attention_mask
        attn = F.softmax(attn, dim=-1, dtype=torch.float32).to(hidden_states.dtype)
        attn = self.dropout(attn)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


class FlashAttentionWrapper(nn.Module):
    """FlashAttention-style wrapper leveraging PyTorch 2.0 SDPA when available."""

    def __init__(
        self,
        hidden_size: int,
        num_attention_heads: int,
        dropout: float = 0.0,
        device=None,
        dtype=None,
    ):
        super().__init__()
        if hidden_size % num_attention_heads != 0:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        self.num_attention_heads = num_attention_heads
        self.head_dim = hidden_size // num_attention_heads
        self.q_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.k_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.v_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.o_proj = nn.Linear(hidden_size, hidden_size, bias=False, device=device, dtype=dtype)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self, hidden_states: torch.Tensor, attention_mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        B, T, C = hidden_states.shape
        q = (
            self.q_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        k = (
            self.k_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        v = (
            self.v_proj(hidden_states)
            .view(B, T, self.num_attention_heads, self.head_dim)
            .transpose(1, 2)
        )
        scale = self.head_dim**-0.5
        q = q * scale
        out = F.scaled_dot_product_attention(
            q, k, v, attn_mask=attention_mask, dropout_p=self.dropout.p if self.training else 0.0
        )
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)
