import math

import torch
import torch.nn.functional as F


def compute_perplexity(loss):
    if isinstance(loss, torch.Tensor):
        loss = loss.item()
    if loss >= 100:
        return float("inf")
    try:
        return math.exp(loss)
    except OverflowError:
        return float("inf")


def masked_loss(logits, labels, ignore_index: int = -100):
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()
    loss = F.cross_entropy(
        shift_logits.view(-1, shift_logits.size(-1)),
        shift_labels.view(-1),
        ignore_index=ignore_index,
    )
    return loss


def compute_accuracy(logits, labels, ignore_index: int = -100):
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()
    preds = shift_logits.argmax(dim=-1)
    mask = shift_labels != ignore_index
    correct = (preds == shift_labels) & mask
    return correct.sum().item() / max(mask.sum().item(), 1)


@torch.no_grad()
def evaluate_metrics(model, dataloader, device, max_batches=None):
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_tokens = 0
    count = 0
    for batch in dataloader:
        input_ids = batch["input_ids"].to(device)
        labels = batch["labels"].to(device)
        outputs = model(input_ids, labels=labels, use_gradient_checkpointing=False)
        loss = outputs["loss"]
        total_loss += loss.item()

        logits = outputs["logits"]
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        preds = shift_logits.argmax(dim=-1)
        mask = shift_labels != -100
        total_correct += ((preds == shift_labels) & mask).sum().item()
        total_tokens += mask.sum().item()
        count += 1
        if max_batches is not None and count >= max_batches:
            break
    avg_loss = total_loss / max(count, 1)
    accuracy = total_correct / max(total_tokens, 1)
    return {
        "loss": avg_loss,
        "perplexity": compute_perplexity(avg_loss),
        "accuracy": accuracy,
    }


@torch.no_grad()
def evaluate_loss(model, dataloader, device, max_batches=None):
    metrics = evaluate_metrics(model, dataloader, device, max_batches=max_batches)
    return metrics["loss"]


class MetricsLogger:
    def __init__(self, log_dir: str, project: Optional[str] = None):
        self.log_dir = log_dir
        self.project = project
        os.makedirs(log_dir, exist_ok=True)
        self._file = open(os.path.join(log_dir, "metrics.log"), "a", encoding="utf-8")

    def log_metrics(self, metrics: dict, step: int):
        line = f"{step} " + " ".join(f"{k}={v}" for k, v in metrics.items())
        self._file.write(line + "\n")
        self._file.flush()

    def close(self):
        if self._file:
            self._file.close()


class TrainingMetrics:
    def __init__(self):
        self._loss = 0.0
        self._count = 0

    def update(self, loss: float, tokens: int):
        self._loss += loss
        self._count += tokens

    def compute(self) -> dict:
        return {"loss": self._loss / max(self._count, 1)}
