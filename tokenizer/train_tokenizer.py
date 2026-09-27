import argparse
import json
import os
import sys
from pathlib import Path

from datasets import load_dataset
from tokenizers import ByteLevelBPETokenizer, BertWordPieceTokenizer
from tokenizers.pre_tokenizers import Whitespace, ByteLevel, BertPreTokenizer


def load_texts_from_jsonl(path: str, text_field: str = "text") -> list[str]:
    texts = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = obj.get(text_field)
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
    return texts


def load_texts_from_parquet(path: str, text_column: str = "text") -> list[str]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError("pandas is required to read parquet files. Install it with: pip install pandas pyarrow") from exc

    df = pd.read_parquet(path, columns=[text_column])
    texts = df[text_column].dropna().astype(str).tolist()
    return [t.strip() for t in texts if t.strip()]


def load_texts_from_hf(dataset_name: str, config_name: str | None = None, split: str = "train", text_column: str = "text", limit: int | None = None) -> list[str]:
    ds = load_dataset(dataset_name, config_name, split=split, streaming=True)
    texts = []
    for example in ds:
        text = example.get(text_column)
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
        if limit is not None and len(texts) >= limit:
            break
    return texts


def train_tokenizer(
    output_dir: str,
    input_paths: list[str],
    tokenizer_type: str = "bpe",
    vocab_size: int = 50257,
    min_frequency: int = 2,
    special_tokens: list[str] | None = None,
    limit: int | None = None,
):
    os.makedirs(output_dir, exist_ok=True)

    texts: list[str] = []
    for path in input_paths:
        path = path.strip()
        if not path:
            continue
        ext = Path(path).suffix.lower()
        if ext == ".jsonl":
            texts.extend(load_texts_from_jsonl(path))
        elif ext in {".parquet", ".pq"}:
            texts.extend(load_texts_from_parquet(path))
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                texts.append(f.read())

    if limit is not None:
        texts = texts[:limit]

    if not texts:
        raise ValueError("No texts found in input paths.")

    if tokenizer_type.lower() == "bpe":
        tokenizer = ByteLevelBPETokenizer()
        tokenizer.pre_tokenizer = ByteLevel()
        tokenizer.train_from_iterator(
            texts,
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=special_tokens or ["<s>", "<pad>", "</s>", "<unk>"],
        )
    elif tokenizer_type.lower() == "wordpiece":
        tokenizer = BertWordPieceTokenizer()
        tokenizer.pre_tokenizer = BertPreTokenizer()
        tokenizer.train_from_iterator(
            texts,
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=special_tokens or ["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]"],
        )
    else:
        raise ValueError(f"Unsupported tokenizer type: {tokenizer_type}")

    tokenizer.save(os.path.join(output_dir, "tokenizer.json"))

    vocab_path = os.path.join(output_dir, "vocab.json")
    merges_path = os.path.join(output_dir, "merges.txt")
    tokenizer.model.save(output_dir)

    print(f"Tokenizer saved to: {output_dir}")
    print(f"Vocab size: {tokenizer.get_vocab_size()}")


def main():
    parser = argparse.ArgumentParser(description="Train BPE or WordPiece tokenizer on custom datasets")
    parser.add_argument("--output-dir", required=True, help="Directory to save tokenizer files")
    parser.add_argument("--input", nargs="+", required=True, help="Input files (.txt, .jsonl, .parquet)")
    parser.add_argument("--type", choices=["bpe", "wordpiece"], default="bpe", help="Tokenizer algorithm")
    parser.add_argument("--vocab-size", type=int, default=50257, help="Target vocabulary size")
    parser.add_argument("--min-frequency", type=int, default=2, help="Minimum token frequency")
    parser.add_argument("--special-tokens", nargs="+", default=None, help="Special tokens")
    parser.add_argument("--limit", type=int, default=None, help="Max number of documents")
    args = parser.parse_args()
    train_tokenizer(
        output_dir=args.output_dir,
        input_paths=args.input,
        tokenizer_type=args.type,
        vocab_size=args.vocab_size,
        min_frequency=args.min_frequency,
        special_tokens=args.special_tokens,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
