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
