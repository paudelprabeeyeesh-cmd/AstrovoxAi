import torch
from torch.utils.data import Dataset, DataLoader
from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import ByteLevel
from tokenizers.decoders import ByteLevel as ByteLevelDecoder
import os


class TextDataset(Dataset):
    def __init__(self, file_path, tokenizer, block_size=1024):
        self.examples = []
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        tokenized = tokenizer.encode(text).ids
        for i in range(0, len(tokenized) - block_size, block_size):
            self.examples.append({
                "input_ids": tokenized[i:i + block_size],
                "labels": tokenized[i + 1:i + 1 + block_size],
            })

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        return self.examples[idx]


def collate_fn(batch, pad_token_id=0):
    input_ids = [torch.tensor(x["input_ids"], dtype=torch.long) for x in batch]
    labels = [torch.tensor(x["labels"], dtype=torch.long) for x in batch]
    input_ids = torch.nn.utils.rnn.pad_sequence(input_ids, batch_first=True, padding_value=pad_token_id)
    labels = torch.nn.utils.rnn.pad_sequence(labels, batch_first=True, padding_value=-100)
    return {"input_ids": input_ids, "labels": labels}


def train_tokenizer_from_files(files, vocab_size=32000, save_path="tokenizer.json"):
    tokenizer = Tokenizer(BPE(unk_token="<unk>"))
    tokenizer.pre_tokenizer = ByteLevel()
    tokenizer.decoder = ByteLevelDecoder()
    trainer = BpeTrainer(vocab_size=vocab_size, special_tokens=["<unk>", "<pad>", "<bos>", "<eos>"])
    tokenizer.train(files, trainer)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    tokenizer.save(save_path)
    return tokenizer


def load_tokenizer(tokenizer_path="tokenizer.json"):
    return Tokenizer.from_file(tokenizer_path)
