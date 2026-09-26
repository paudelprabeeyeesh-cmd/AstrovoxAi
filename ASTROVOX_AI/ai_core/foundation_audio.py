import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioLanguageConfig:
    vocab_size: int = 50257
    audio_dim: int = 128
    hidden_size: int = 768
    num_layers: int = 12
    num_heads: int = 12
    dropout: float = 0.1
    num_audio_tokens: int = 8192


class AudioEncoder(nn.Module):
    def __init__(self, config: AudioLanguageConfig):
        super().__init__()
        self.config = config
        self.conv1 = nn.Conv1d(1, config.hidden_size, kernel_size=3, stride=2, padding=1)
        self.conv2 = nn.Conv1d(config.hidden_size, config.hidden_size, kernel_size=3, stride=2, padding=1)
        self.conv3 = nn.Conv1d(config.hidden_size, config.hidden_size, kernel_size=3, stride=2, padding=1)
        self.ln = nn.LayerNorm(config.hidden_size)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, audio):
        x = self.conv1(audio)
        x = F.gelu(x)
        x = self.conv2(x)
        x = F.gelu(x)
        x = self.conv3(x)
        x = F.gelu(x)
        x = x.transpose(1, 2)
        x = self.ln(x)
        return self.dropout(x)


class AudioLanguageModel(nn.Module):
    def __init__(self, config: Optional[AudioLanguageConfig] = None):
        super().__init__()
        self.config = config or AudioLanguageConfig()
        self.audio_encoder = AudioEncoder(self.config)
        self.audio_proj = nn.Linear(self.config.hidden_size, self.config.hidden_size)
        self.text_embedding = nn.Embedding(self.config.vocab_size, self.config.hidden_size)
        self.pos_embedding = nn.Embedding(1024, self.config.hidden_size)
        self.dropout = nn.Dropout(self.config.dropout)
        self.blocks = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model=self.config.hidden_size,
                nhead=self.config.num_heads,
                dim_feedforward=self.config.hidden_size * 4,
                dropout=self.config.dropout,
                activation='gelu',
                batch_first=True,
            ) for _ in range(self.config.num_layers)
        ])
        self.ln_f = nn.LayerNorm(self.config.hidden_size)
        self.lm_head = nn.Linear(self.config.hidden_size, self.config.vocab_size, bias=False)
        logger.info("AudioLanguage model initialized")

    def encode_audio(self, audio):
        return self.audio_encoder(audio)

    def encode_text(self, text):
        return self.text_embedding(text)

    def forward(self, audio, text_input_ids, labels=None):
        audio_emb = self.audio_encoder(audio)
        audio_emb = self.audio_proj(audio_emb)
        text_emb = self.text_embedding(text_input_ids)
        if audio_emb.size(1) > 0:
            x = torch.cat([audio_emb, text_emb], dim=1)
        else:
            x = text_emb
        seq_len = x.size(1)
        pos = torch.arange(seq_len, device=x.device).unsqueeze(0)
        x = self.dropout(x + self.pos_embedding(pos))
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        logits = self.lm_head(x)
        loss = None
        if labels is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1))
        return {"logits": logits, "loss": loss, "audio_emb": audio_emb, "text_emb": text_emb}


class AudioLanguageTrainer:
    def __init__(self, model, optimizer=None, scheduler=None, device=None, grad_clip=1.0):
        self.model = model
        self.optimizer = optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.01)
        self.scheduler = scheduler
        self.device = device or torch.device("cpu")
        self.grad_clip = grad_clip
        self.model.to(self.device)
        logger.info("AudioLanguageTrainer initialized")

    def train_step(self, audio_batch, text_batch):
        self.model.train()
        audio = audio_batch["audio"].to(self.device)
        text_ids = text_batch["input_ids"].to(self.device)
        labels = text_batch.get("labels")
        if labels is not None:
            labels = labels.to(self.device)
        outputs = self.model(audio, text_ids, labels=labels)
        loss = outputs["loss"]
        loss.backward()
        if self.grad_clip > 0:
            nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
        self.optimizer.step()
        if self.scheduler:
            self.scheduler.step()
        self.optimizer.zero_grad()
        return {"loss": loss.item()}
