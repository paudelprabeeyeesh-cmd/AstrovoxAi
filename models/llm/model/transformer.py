import torch
import torch.nn as nn
import torch.nn.functional as F


class LayerNorm(nn.Module):
    def __init__(self, hidden_size, eps=1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.bias = nn.Parameter(torch.zeros(hidden_size))
        self.eps = eps

    def forward(self, hidden_states):
        variance = hidden_states.pow(2).mean(-1, keepdim=True)
        hidden_states = hidden_states / torch.sqrt(variance + self.eps)
        return self.weight * hidden_states + self.bias


class CausalSelfAttention(nn.Module):
    def __init__(self, hidden_size, num_attention_heads, dropout=0.0, max_position_embeddings=1024):
        super().__init__()
        assert hidden_size % num_attention_heads == 0
        self.num_attention_heads = num_attention_heads
        self.head_dim = hidden_size // num_attention_heads
        self.scale = self.head_dim ** -0.5

        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.o_proj = nn.Linear(hidden_size, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.max_position_embeddings = max_position_embeddings
        self.register_buffer(
            "bias",
            torch.tril(torch.ones(max_position_embeddings, max_position_embeddings))
            .view(1, 1, max_position_embeddings, max_position_embeddings),
        )

    def forward(self, hidden_states, attention_mask=None):
        B, T, C = hidden_states.size()
        q = self.q_proj(hidden_states).view(B, T, self.num_attention_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(hidden_states).view(B, T, self.num_attention_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(hidden_states).view(B, T, self.num_attention_heads, self.head_dim).transpose(1, 2)

        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.masked_fill(self.bias[:, :, :T, :T] == 0, float("-inf"))
        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)

        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.o_proj(out)


class MLP(nn.Module):
    def __init__(self, hidden_size, intermediate_size, dropout=0.0):
        super().__init__()
        self.up_proj = nn.Linear(hidden_size, intermediate_size)
        self.act = nn.GELU()
        self.down_proj = nn.Linear(intermediate_size, hidden_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, hidden_states):
        hidden_states = self.up_proj(hidden_states)
        hidden_states = self.act(hidden_states)
        hidden_states = self.down_proj(hidden_states)
        return self.dropout(hidden_states)


class TransformerBlock(nn.Module):
    def __init__(self, hidden_size, num_attention_heads, intermediate_size, dropout=0.0, max_position_embeddings=1024, layer_norm_epsilon=1e-5):
        super().__init__()
        self.ln_1 = LayerNorm(hidden_size, eps=layer_norm_epsilon)
        self.attn = CausalSelfAttention(hidden_size, num_attention_heads, dropout, max_position_embeddings)
        self.ln_2 = LayerNorm(hidden_size, eps=layer_norm_epsilon)
        self.mlp = MLP(hidden_size, intermediate_size, dropout)

    def forward(self, hidden_states):
        hidden_states = hidden_states + self.attn(self.ln_1(hidden_states))
        hidden_states = hidden_states + self.mlp(self.ln_2(hidden_states))
        return hidden_states


class OutputLayer(nn.Module):
    def __init__(self, hidden_size, vocab_size):
        super().__init__()
        self.lm_head = nn.Linear(hidden_size, vocab_size, bias=False)

    def forward(self, hidden_states):
        return self.lm_head(hidden_states)
