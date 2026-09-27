import json
import os
import random
from typing import List, Dict, Iterator, Optional

import torch


class InstructionCollator:
    def __init__(self, pad_token_id: int = 0, max_length: int = 1024):
        self.pad_token_id = pad_token_id
        self.max_length = max_length

    def __call__(self, batch):
        input_ids = [torch.tensor(x["input_ids"][: self.max_length], dtype=torch.long) for x in batch]
        labels = [torch.tensor(x["labels"][: self.max_length], dtype=torch.long) for x in batch]
        input_ids = torch.nn.utils.rnn.pad_sequence(input_ids, batch_first=True, padding_value=self.pad_token_id)
        labels = torch.nn.utils.rnn.pad_sequence(labels, batch_first=True, padding_value=-100)
        return {"input_ids": input_ids, "labels": labels}


class InstructionDataset:
    def __init__(self, path: str, tokenizer, block_size: int = 1024, system_prompt: str = "You are a helpful assistant."):
        self.path = path
        self.tokenizer = tokenizer
        self.block_size = block_size
        self.system_prompt = system_prompt
        self.examples = []
        self._load()

    def _format_example(self, instruction: str, input_text: str = "", output_text: str = "") -> str:
        if input_text:
            prompt = f"<s>[INST] {self.system_prompt}\n\n{instruction}\n\n{input_text} [/INST]"
        else:
            prompt = f"<s>[INST] {self.system_prompt}\n\n{instruction} [/INST]"
        response = f" {output_text}</s>"
        return prompt + response

    def _load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                sample = json.loads(line)
                instruction = sample.get("instruction", "")
                input_text = sample.get("input", "")
                output_text = sample.get("output", "")
                text = self._format_example(instruction, input_text, output_text)
                tokenized = self.tokenizer.encode(text).ids
                for i in range(0, max(len(tokenized) - self.block_size, 0), self.block_size):
                    chunk = tokenized[i:i + self.block_size]
                    labels = chunk[1:] + [-100]
                    self.examples.append({"input_ids": chunk, "labels": labels})

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        return self.examples[idx]


class StreamingTextDataset:
    def __init__(self, path: str, tokenizer, block_size: int = 1024, stride: int = 512):
        self.path = path
        self.tokenizer = tokenizer
        self.block_size = block_size
        self.stride = stride
        self._index = self._build_index()
        self._file_handle = None

    def _build_index(self) -> List[int]:
        target = self.path
        if not os.path.exists(target) and os.path.exists(target + ".txt"):
            target = target + ".txt"
        offsets = []
        with open(target, "rb") as f:
            offsets.append(f.tell())
            while f.readline():
                offsets.append(f.tell())
        return offsets[:-1]

    def _get_file_handle(self):
        if self._file_handle is None:
            target = self.path
            if not os.path.exists(target) and os.path.exists(target + ".txt"):
                target = target + ".txt"
            self._file_handle = open(target, "r", encoding="utf-8")
        return self._file_handle

    def __len__(self):
        return len(self._index)

    def __getitem__(self, idx):
        f = self._get_file_handle()
        f.seek(self._index[idx])
        text = f.readline()
        tokenized = self.tokenizer.encode(text).ids
        start = 0
        if len(tokenized) > self.block_size:
            start = random.randint(0, max(len(tokenized) - self.block_size, 0))
        chunk = tokenized[start:start + self.block_size]
        labels = chunk[1:] + [-100]
        return {"input_ids": chunk, "labels": labels}

    def close(self):
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None

    def __del__(self):
        self.close()


class PretrainDataset:
    def __init__(self, path: str, tokenizer, block_size: int = 1024, streaming: bool = False):
        self.path = path
        self.tokenizer = tokenizer
        self.block_size = block_size
        self.streaming = streaming
        if streaming:
            self._inner = StreamingTextDataset(path, tokenizer, block_size=block_size)
            self._len = len(self._inner)
        else:
            self.examples = []
            self._load_all()
            self._len = len(self.examples)

    def _load_all(self):
        with open(self.path, "r", encoding="utf-8") as f:
            text = f.read()
        tokenized = self.tokenizer.encode(text).ids
        for i in range(0, len(tokenized) - self.block_size, self.block_size):
            self.examples.append({
                "input_ids": tokenized[i:i + self.block_size],
                "labels": tokenized[i + 1:i + 1 + self.block_size],
            })

    def __len__(self):
        return self._len

    def __getitem__(self, idx):
        if self.streaming:
            return self._inner[idx]
        return self.examples[idx]

    def close(self):
        if self.streaming:
            self._inner.close()


def prepare_pretrain_dataset(input_path: str, output_path: str, tokenizer, block_size: int = 1024):
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(input_path, "r", encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        buffer = []
        for line in fin:
            buffer.append(line.strip())
            combined = " ".join(buffer)
            tokenized = tokenizer.encode(combined).ids
            if len(tokenized) >= block_size:
                chunks = [tokenized[i:i + block_size] for i in range(0, len(tokenized) - block_size + 1, block_size)]
                for chunk in chunks:
                    text = tokenizer.decode(chunk)
                    fout.write(json.dumps({"text": text}) + "\n")
                buffer = []
        if buffer:
            combined = " ".join(buffer)
            tokenized = tokenizer.encode(combined).ids
            if len(tokenized) > 0:
                chunks = [tokenized[i:i + block_size] for i in range(0, len(tokenized) - block_size + 1, block_size)]
                for chunk in chunks:
                    text = tokenizer.decode(chunk)
                    fout.write(json.dumps({"text": text}) + "\n")


def create_dataloader(dataset, batch_size: int = 1, shuffle: bool = True, num_workers: int = 0, pad_token_id: int = 0, max_length: int = 1024):
    from torch.utils.data import DataLoader
    collator = InstructionCollator(pad_token_id=pad_token_id, max_length=max_length)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers, collate_fn=collator)
