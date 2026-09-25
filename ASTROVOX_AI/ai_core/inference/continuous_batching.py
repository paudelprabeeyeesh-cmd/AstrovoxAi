from typing import List, Optional, Dict
import torch
import torch.nn as nn


class ContinuousBatcher:
    def __init__(self, max_batch_size: int, max_seq_len: int, pad_token_id: int = 0):
        self.max_batch_size = max_batch_size
        self.max_seq_len = max_seq_len
        self.pad_token_id = pad_token_id
        self.active_sequences: List[Dict] = []
        self.completed_sequences: List[Dict] = []

    def add_sequence(self, seq_id: str, tokens: List[int], max_new_tokens: int) -> Optional[Dict]:
        if len(self.active_sequences) >= self.max_batch_size:
            return None
        seq = {'id': seq_id, 'tokens': tokens, 'generated': 0, 'max_new_tokens': max_new_tokens, 'finished': False}
        self.active_sequences.append(seq)
        return seq

    def step(self, model: nn.Module, device: torch.device) -> List[Dict]:
        if not self.active_sequences:
            return []
        batch = self._prepare_batch()
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        with torch.no_grad():
            logits = model(input_ids)
        next_token_logits = logits[:, -1, :]
        next_tokens = torch.argmax(next_token_logits, dim=-1)
        results = []
        for i, seq in enumerate(self.active_sequences):
            if not seq['finished']:
                next_token = next_tokens[i].item()
                seq['tokens'].append(next_token)
                seq['generated'] += 1
                if seq['generated'] >= seq['max_new_tokens']:
                    seq['finished'] = True
                    self.completed_sequences.append(seq)
                    results.append(seq)
        self.active_sequences = [seq for seq in self.active_sequences if not seq['finished']]
        return results

    def _prepare_batch(self) -> Dict:
        batch_size = len(self.active_sequences)
        input_ids = torch.full((batch_size, self.max_seq_len), self.pad_token_id, dtype=torch.long)
        attention_mask = torch.zeros(batch_size, self.max_seq_len, dtype=torch.long)
        for i, seq in enumerate(self.active_sequences):
            length = len(seq['tokens'])
            input_ids[i, :length] = torch.tensor(seq['tokens'], dtype=torch.long)
            attention_mask[i, :length] = 1
        return {'input_ids': input_ids, 'attention_mask': attention_mask}
