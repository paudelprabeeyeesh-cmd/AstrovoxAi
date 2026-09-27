import argparse
import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Optional

try:
    from datasets import load_dataset
except Exception:
    load_dataset = None
from tokenizers import Tokenizer
try:
    from tokenizers.decoders import ByteLevelDecoder, WordPiece as WordPieceDecoder
except Exception:
    ByteLevelDecoder = None
    WordPieceDecoder = None
from tokenizers.models import BPE, WordPiece
from tokenizers.pre_tokenizers import ByteLevel, Whitespace
from tokenizers.processors import TemplateProcessing
from tokenizers.trainers import BpeTrainer, WordPieceTrainer
try:
    from tokenizers.decoders import BPEDecoder, WordPiece as WordPieceDecoder2
except Exception:
    BPEDecoder = None
    WordPieceDecoder2 = None


def _get_decoder(algorithm: str):
    if algorithm == "bpe":
        if ByteLevelDecoder is not None:
            return ByteLevelDecoder()
        if BPEDecoder is not None:
            return BPEDecoder()
        raise ImportError("No BPE decoder available in tokenizers library")
    if algorithm == "wordpiece":
        if WordPieceDecoder is not None:
            return WordPieceDecoder()
        if WordPieceDecoder2 is not None:
            return WordPieceDecoder2()
        raise ImportError("No WordPiece decoder available in tokenizers library")
    raise ValueError(f"Unsupported algorithm: {algorithm}. Choose 'bpe' or 'wordpiece'.")


SPECIAL_TOKENS = {
    "pad": "<pad>",
    "eos": "<eos>",
    "bos": "<bos>",
    "unk": "<unk>",
    "mask": "<mask>",
}
SPECIAL_TOKENS_LIST = list(SPECIAL_TOKENS.values())


def clean_text(text: str) -> str:
    """Normalize and clean raw text.

    Applies NFKC normalization, strips URLs, and collapses whitespace.
    """
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _dedup_iterator(texts: Iterable[str]) -> Iterable[str]:
    """Yield unique texts using SHA-256 deduplication."""
    seen: set[str] = set()
    for text in texts:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key not in seen:
            seen.add(key)
            yield text


def iter_texts(
    paths: list[str],
    text_key: str = "text",
    deduplicate: bool = True,
    clean: bool = True,
    limit: Optional[int] = None,
) -> Iterable[str]:
    """Stream text documents from multiple input sources.

    Supported formats:
    - Local .txt, .jsonl, .parquet files
    - HuggingFace datasets via hf://dataset/config
    """

    def _process(text: str) -> Optional[str]:
        if clean:
            text = clean_text(text)
        return text if text else None

    def _gen() -> Iterable[str]:
        for path in paths:
            path = path.strip()
            if not path:
                continue

            if path.startswith("hf://"):
                repo_id = path[5:]
                if "/" not in repo_id:
                    raise ValueError(f"Invalid hf:// path: {path}")
                parts = repo_id.split("/")
                dataset = "/".join(parts[:2])
                config = "/".join(parts[2:]) if len(parts) > 2 else None

                ds = load_dataset(dataset, config, streaming=True)
                split = next(iter(ds))
                for ex in ds[split]:
                    text = ex.get(text_key, "")
                    processed = _process(text)
                    if processed:
                        yield processed
                continue

            ext = Path(path).suffix.lower()
            if ext == ".txt":
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        processed = _process(line)
                        if processed:
                            yield processed
            elif ext == ".jsonl":
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        text = obj.get(text_key, "")
                        processed = _process(text)
                        if processed:
                            yield processed
            elif ext in (".parquet", ".pq"):
                try:
                    import pyarrow.parquet as pq
                except ImportError as exc:
                    raise ImportError(
                        "pyarrow is required to read parquet files. "
                        "Install it with: pip install pyarrow"
                    ) from exc

                pf = pq.ParquetFile(path)
                for batch in pf.iter_batches(batch_size=1024):
                    for ex in batch.to_pylist():
                        text = ex.get(text_key, "")
                        processed = _process(text)
                        if processed:
                            yield processed
            else:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        processed = _process(line)
                        if processed:
                            yield processed

    iterator: Iterable[str] = _gen()
    if deduplicate:
        iterator = _dedup_iterator(iterator)

    if limit is not None:
        def _limit(it: Iterable[str], n: int) -> Iterable[str]:
            count = 0
            for item in it:
                if count >= n:
                    break
                count += 1
                yield item

        iterator = _limit(iterator, limit)

    return iterator


def train_tokenizer(
    paths: list[str],
    vocab_size: int = 32000,
    algorithm: str = "bpe",
    save_dir: str = "tokenizer",
    special_tokens: Optional[list[str]] = None,
    text_key: str = "text",
    limit: Optional[int] = None,
    cleaning: bool = True,
    deduplicate: bool = True,
) -> Tokenizer:
    """Train a BPE or WordPiece tokenizer on the provided text sources.

    Args:
        paths: Input paths (.txt, .jsonl, .parquet) or hf://dataset/config.
        vocab_size: Target vocabulary size (e.g., 32000, 50000, 64000, 128000).
        algorithm: Tokenizer algorithm. Choose 'bpe' or 'wordpiece'.
        save_dir: Directory to save tokenizer.json and tokenizer_config.json.
        special_tokens: List of special tokens. Defaults to standard set.
        text_key: Key for the text field in JSON/Parquet/HF datasets.
        limit: Maximum number of documents to process.
        cleaning: Enable NFKC normalization and URL stripping.
        deduplicate: Remove duplicate documents.

    Returns:
        Trained Tokenizer instance.
    """
    if not paths:
        raise ValueError("No input paths provided.")

    if special_tokens is None:
        special_tokens = SPECIAL_TOKENS_LIST

    if algorithm == "bpe":
        model = BPE(unk_token=SPECIAL_TOKENS["unk"])
        trainer = BpeTrainer(
            vocab_size=vocab_size,
            special_tokens=special_tokens,
            min_frequency=2,
        )
        pre_tokenizer = ByteLevel()
        decoder = _get_decoder("bpe")
    elif algorithm == "wordpiece":
        model = WordPiece(unk_token=SPECIAL_TOKENS["unk"])
        trainer = WordPieceTrainer(
            vocab_size=vocab_size,
            special_tokens=special_tokens,
            min_frequency=2,
        )
        pre_tokenizer = Whitespace()
        decoder = _get_decoder("wordpiece")
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}. Choose 'bpe' or 'wordpiece'.")

    tokenizer = Tokenizer(model)
    tokenizer.pre_tokenizer = pre_tokenizer
    tokenizer.decoder = decoder

    iterator = iter_texts(
        paths,
        text_key=text_key,
        deduplicate=deduplicate,
        clean=cleaning,
        limit=limit,
    )

    tokenizer.train_from_iterator(iterator, trainer)

    tokenizer.post_processor = TemplateProcessing(
        single="$A",
        pair="$A $B",
        special_tokens=[
            (SPECIAL_TOKENS["bos"], tokenizer.token_to_id(SPECIAL_TOKENS["bos"])),
            (SPECIAL_TOKENS["eos"], tokenizer.token_to_id(SPECIAL_TOKENS["eos"])),
        ],
    )

    os.makedirs(save_dir, exist_ok=True)
    tokenizer.save(os.path.join(save_dir, "tokenizer.json"))

    config = {
        "model_type": algorithm,
        "unk_token": SPECIAL_TOKENS["unk"],
        "bos_token": SPECIAL_TOKENS["bos"],
        "eos_token": SPECIAL_TOKENS["eos"],
        "pad_token": SPECIAL_TOKENS["pad"],
        "mask_token": SPECIAL_TOKENS["mask"],
        "vocab_size": tokenizer.get_vocab_size(),
    }
    with open(os.path.join(save_dir, "tokenizer_config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    return tokenizer


def load_tokenizer(tokenizer_path: str = "tokenizer.json") -> Tokenizer:
    """Load a tokenizer from a file or directory.

    Args:
        tokenizer_path: Path to tokenizer.json or directory containing it.

    Returns:
        Loaded Tokenizer instance.
    """
    if os.path.isdir(tokenizer_path):
        tokenizer_path = os.path.join(tokenizer_path, "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        raise FileNotFoundError(f"Tokenizer not found at {tokenizer_path}")
    return Tokenizer.from_file(tokenizer_path)


class TextDataset:
    """PyTorch Dataset for language modeling."""

    def __init__(self, file_path: str, tokenizer: Tokenizer, block_size: int = 1024):
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
    """Collate function for PyTorch DataLoader."""
    import torch
    from torch.nn.utils.rnn import pad_sequence

    input_ids = [torch.tensor(x["input_ids"], dtype=torch.long) for x in batch]
    labels = [torch.tensor(x["labels"], dtype=torch.long) for x in batch]
    input_ids = pad_sequence(input_ids, batch_first=True, padding_value=pad_token_id)
    labels = pad_sequence(labels, batch_first=True, padding_value=-100)
    return {"input_ids": input_ids, "labels": labels}


def train_tokenizer_from_files(
    files: list[str],
    vocab_size: int = 32000,
    save_path: str = "tokenizer.json",
) -> Tokenizer:
    """Backward-compatible wrapper around train_tokenizer."""
    save_dir = os.path.dirname(save_path) or "."
    return train_tokenizer(
        paths=files,
        vocab_size=vocab_size,
        save_dir=save_dir,
    )


def create_dummy_tokenizer(
    save_dir: str = "tokenizer",
    vocab_size: int = 32000,
    algorithm: str = "bpe",
) -> Tokenizer:
    """Create and save a small dummy tokenizer for testing.

    Args:
        save_dir: Directory to save the tokenizer.
        vocab_size: Target vocabulary size.
        algorithm: Tokenizer algorithm ('bpe' or 'wordpiece').

    Returns:
        Trained Tokenizer instance.
    """
    dummy_text = (
        "Hello world! This is a test sentence for the dummy tokenizer. "
        "The quick brown fox jumps over the lazy dog. "
        "Artificial intelligence is transforming the world. "
        "Machine learning models require data to train. "
        "Natural language processing enables computers to understand text. "
        "Deep learning uses neural networks with many layers. "
        "Transformers have revolutionized sequence modeling. "
        "Attention mechanisms help models focus on relevant parts. "
        "Tokenization splits text into smaller units called tokens. "
        "Byte Pair Encoding is a popular tokenization algorithm. "
    ) * 2000

    os.makedirs(save_dir, exist_ok=True)
    temp_path = os.path.join(save_dir, "_dummy_train.txt")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(dummy_text)

        tokenizer = train_tokenizer(
            paths=[temp_path],
            vocab_size=vocab_size,
            algorithm=algorithm,
            save_dir=save_dir,
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return tokenizer


def main():
    parser = argparse.ArgumentParser(
        description="Train a BPE or WordPiece tokenizer on text data."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Input files (.txt, .jsonl, .parquet) or hf://dataset/config",
    )
    parser.add_argument(
        "--vocab-size",
        type=int,
        default=32000,
        help="Vocabulary size (default: 32000)",
    )
    parser.add_argument(
        "--algorithm",
        choices=["bpe", "wordpiece"],
        default="bpe",
        help="Tokenizer algorithm (default: bpe)",
    )
    parser.add_argument(
        "--save-dir",
        default="tokenizer",
        help="Output directory (default: tokenizer)",
    )
    parser.add_argument(
        "--text-key",
        default="text",
        help="Key for text field in JSON/Parquet/HF datasets (default: text)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of examples",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Disable deduplication",
    )
    parser.add_argument(
        "--no-cleaning",
        action="store_true",
        help="Disable NFKC normalization and URL stripping",
    )
    parser.add_argument(
        "--dummy",
        action="store_true",
        help="Create a dummy tokenizer for testing",
    )

    args = parser.parse_args()

    if args.dummy:
        tokenizer = create_dummy_tokenizer(
            save_dir=args.save_dir,
            vocab_size=args.vocab_size,
            algorithm=args.algorithm,
        )
        print(f"Dummy tokenizer saved to {args.save_dir}")
        return

    tokenizer = train_tokenizer(
        paths=args.paths,
        vocab_size=args.vocab_size,
        algorithm=args.algorithm,
        save_dir=args.save_dir,
        text_key=args.text_key,
        limit=args.limit,
        cleaning=not args.no_cleaning,
        deduplicate=not args.no_dedup,
    )
    print(f"Tokenizer saved to {args.save_dir}")


if __name__ == "__main__":
    main()
