import math
import torch
import torch.nn.functional as F


def compute_perplexity(model, dataloader, device, max_batches=100):
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    with torch.no_grad():
        for i, batch in enumerate(dataloader):
            if i >= max_batches:
                break
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            outputs = model(input_ids, labels=labels)
            loss = outputs["loss"]
            total_loss += loss.item() * input_ids.numel()
            total_tokens += input_ids.numel()
    model.train()
    if total_tokens == 0:
        return float("inf")
    avg_loss = total_loss / total_tokens
    return math.exp(avg_loss)


def validate(model, dataloader, device, max_batches=100):
    model.eval()
    total_loss = 0.0
    count = 0
    with torch.no_grad():
        for i, batch in enumerate(dataloader):
            if i >= max_batches:
                break
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            outputs = model(input_ids, labels=labels)
            total_loss += outputs["loss"].item()
            count += 1
    model.train()
    return total_loss / max(count, 1)
