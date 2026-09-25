from typing import Optional, Tuple, List
import torch
import torch.nn as nn


class SpeculativeDecoder(nn.Module):
    def __init__(self, target_model: nn.Module, draft_model: nn.Module, gamma: int = 4):
        super().__init__()
        self.target_model = target_model
        self.draft_model = draft_model
        self.gamma = gamma

    @torch.no_grad()
    def decode(self, input_ids: torch.Tensor, max_new_tokens: int = 100) -> Tuple[torch.Tensor, int]:
        device = input_ids.device
        generated = input_ids.clone()
        num_accepted = 0
        while generated.shape[1] < max_new_tokens:
            draft_tokens = []
            draft_logits = []
            cur = generated
            for _ in range(self.gamma):
                logits = self.draft_model(cur)
                next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
                draft_tokens.append(next_token)
                draft_logits.append(logits[:, -1, :])
                cur = torch.cat([cur, next_token], dim=1)
            target_logits = self.target_model(cur)
            target_logits_at_draft = target_logits[:, generated.shape[1]:-1, :]
            target_next_logit = target_logits[:, -1, :]
            draft_tokens_tensor = torch.cat(draft_tokens, dim=1)
            draft_probs = torch.softmax(torch.stack(draft_logits, dim=1), dim=-1)
            target_probs = torch.softmax(target_logits_at_draft, dim=-1)
            accepted = torch.argmax(draft_probs, dim=-1) == torch.argmax(target_probs, dim=-1)
            accepted = accepted.all(dim=-1)
            for i in range(accepted.shape[0]):
                if accepted[i]:
                    generated = torch.cat([generated, draft_tokens_tensor[i:i+1]], dim=1)
                    num_accepted += self.gamma
                else:
                    mismatch = (~accepted[i]).nonzero(as_tuple=True)[0][0]
                    generated = torch.cat([generated, draft_tokens_tensor[i:i+1, :mismatch+1]], dim=1)
                    num_accepted += mismatch.item()
                    break
            next_token = torch.argmax(target_next_logit, dim=-1, keepdim=True)
            generated = torch.cat([generated, next_token], dim=1)
        return generated, num_accepted
