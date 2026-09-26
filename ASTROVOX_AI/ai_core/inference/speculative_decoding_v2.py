from typing import Tuple, Dict, Any
import torch
import torch.nn as nn
import torch.nn.functional as F


class EnhancedSpeculativeDecoder(nn.Module):
    def __init__(self, target_model: nn.Module, draft_model: nn.Module, gamma: int = 4, use_tree_decoding: bool = False):
        super().__init__()
        self.target_model = target_model
        self.draft_model = draft_model
        self.gamma = gamma
        self.use_tree_decoding = use_tree_decoding

    @torch.no_grad()
    def decode(self, input_ids: torch.Tensor, max_new_tokens: int = 100, temperature: float = 1.0, top_p: float = 0.9) -> Tuple[torch.Tensor, Dict[str, Any]]:
        device = input_ids.device
        generated = input_ids.clone()
        num_accepted = 0
        total_draft_tokens = 0
        while generated.shape[1] < max_new_tokens + input_ids.shape[1]:
            draft_tokens = []
            draft_logits = []
            cur = generated
            for _ in range(self.gamma):
                logits = self.draft_model(cur)
                next_token_logits = logits[:, -1, :] / temperature
                next_token = self._sample(next_token_logits, top_p)
                draft_tokens.append(next_token)
                draft_logits.append(next_token_logits)
                cur = torch.cat([cur, next_token], dim=1)
                total_draft_tokens += 1
            target_logits = self.target_model(cur)
            target_logits_at_draft = target_logits[:, generated.shape[1]:-1, :]
            target_next_logit = target_logits[:, -1, :]
            draft_tokens_tensor = torch.cat(draft_tokens, dim=1)
            draft_probs = torch.softmax(torch.stack(draft_logits, dim=1), dim=-1)
            target_probs = torch.softmax(target_logits_at_draft, dim=-1)
            accepted = self._check_acceptance(draft_probs, target_probs)
            for i in range(accepted.shape[0]):
                if accepted[i]:
                    generated = torch.cat([generated, draft_tokens_tensor[i:i+1]], dim=1)
                    num_accepted += self.gamma
                else:
                    mismatch = (~accepted[i]).nonzero(as_tuple=True)[0][0]
                    generated = torch.cat([generated, draft_tokens_tensor[i:i+1, :mismatch+1]], dim=1)
                    num_accepted += mismatch.item() + 1
                    break
            next_token = torch.argmax(target_next_logit, dim=-1, keepdim=True)
            generated = torch.cat([generated, next_token], dim=1)
        stats = {'accepted': num_accepted, 'total_draft': total_draft_tokens, 'acceptance_rate': num_accepted / max(total_draft_tokens, 1)}
        return generated[:, :max_new_tokens + input_ids.shape[1]], stats

    def _sample(self, logits: torch.Tensor, top_p: float) -> torch.Tensor:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
        sorted_indices_to_remove = cumulative_probs > top_p
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = False
        indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
        logits[indices_to_remove] = float('-inf')
        return torch.multinomial(F.softmax(logits, dim=-1), num_samples=1)

    def _check_acceptance(self, draft_probs: torch.Tensor, target_probs: torch.Tensor) -> torch.Tensor:
        draft_tokens = torch.argmax(draft_probs, dim=-1)
        target_tokens = torch.argmax(target_probs, dim=-1)
        return (draft_tokens == target_tokens).all(dim=-1)


class TreeSpeculativeDecoder(nn.Module):
    def __init__(self, target_model: nn.Module, draft_model: nn.Module, num_draft_tokens: int = 5):
        super().__init__()
        self.target_model = target_model
        self.draft_model = draft_model
        self.num_draft_tokens = num_draft_tokens

    @torch.no_grad()
    def decode(self, input_ids: torch.Tensor, max_new_tokens: int = 100) -> Tuple[torch.Tensor, Dict[str, Any]]:
        device = input_ids.device
        generated = input_ids.clone()
        num_accepted = 0
        total_draft = 0
        while generated.shape[1] < max_new_tokens + input_ids.shape[1]:
            draft_tokens = []
            cur = generated
            for _ in range(self.num_draft_tokens):
                logits = self.draft_model(cur)
                next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
                draft_tokens.append(next_token)
                cur = torch.cat([cur, next_token], dim=1)
            total_draft += self.num_draft_tokens
            all_candidate_ids = torch.cat([generated] + draft_tokens, dim=1)
            target_logits = self.target_model(all_candidate_ids)
            target_probs_at_draft = F.softmax(target_logits[:, generated.shape[1]:-1, :], dim=-1)
            draft_token_ids = torch.cat(draft_tokens, dim=1)
            draft_probs = torch.zeros(target_probs_at_draft.shape, device=device)
            for t in range(self.num_draft_tokens):
                draft_probs[:, t, draft_token_ids[:, t]] = 1.0
            accepted = (draft_probs.argmax(dim=-1) == target_probs_at_draft.argmax(dim=-1)).all(dim=-1)
            accepted_count = accepted.sum().item()
            num_accepted += accepted_count * self.num_draft_tokens
            if accepted.all():
                generated = all_candidate_ids
            else:
                mismatch_idx = (~accepted).nonzero(as_tuple=True)[0][0]
                generated = torch.cat([generated, draft_token_ids[mismatch_idx:mismatch_idx+1, :mismatch_idx+1]], dim=1)
                target_next = torch.argmax(target_logits[:, -1, :], dim=-1, keepdim=True)
                generated = torch.cat([generated, target_next], dim=1)
        stats = {'accepted': num_accepted, 'total_draft': total_draft, 'acceptance_rate': num_accepted / max(total_draft, 1)}
        return generated[:, :max_new_tokens + input_ids.shape[1]], stats
