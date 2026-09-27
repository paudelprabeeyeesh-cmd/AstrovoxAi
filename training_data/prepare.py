import argparse
import hashlib
import os
import re
import unicodedata
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    from datasets import load_dataset
except ImportError:
    load_dataset = None


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def filter_quality(text: str) -> bool:
    if len(text) < 40:
        return False
    if len(text) > 100_000:
        return False
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.5:
        return False
    if text.count("http") > 20:
        return False
    return True


def clean_text(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[^\x00-\x7F\u0080-\u00FF\u0100-\u017F\u2000-\u206F\u2190-\u21FF\u2200-\u22FF]", " ", text)
    text = re.sub(r"[^\w\s.,!?;:'\"\-\(\)\[\]\{\}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def iter_jsonl(path: str) -> Iterable[str]:
    import json
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield obj.get("text") or obj.get("content") or obj.get("prompt", "") + " " + obj.get("completion", "")


def iter_parquet(path: str, text_column: str = "text") -> Iterable[str]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError("pandas is required to read parquet files. Install it with: pip install pandas pyarrow") from exc
    df = pd.read_parquet(path, columns=[text_column])
    for value in df[text_column].dropna().astype(str):
        yield value


def iter_hf(dataset_name: str, config_name: str | None, split: str, text_column: str, limit: int | None) -> Iterable[str]:
    if load_dataset is None:
        raise ImportError("datasets is required. Install it with: pip install datasets")
    ds = load_dataset(dataset_name, config_name, split=split, streaming=True)
    count = 0
    for example in ds:
        text = example.get(text_column)
        if isinstance(text, str) and text.strip():
            yield text
            count += 1
            if limit is not None and count >= limit:
                break


def compute_md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def deduplicate(texts: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for text in texts:
        key = compute_md5(text)
        if key not in seen:
            seen.add(key)
            unique.append(text)
    return unique


def prepare(
    sources: list[str],
    output_path: str,
    fmt: str = "jsonl",
    text_column: str = "text",
    deduplicate_texts: bool = True,
    clean: bool = True,
    limit: int | None = None,
):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    def _source_iter():
        count = 0
        for src in sources:
            src = src.strip()
            if src.startswith("hf://"):
                parts = src[5:].split("/", 1)
                dataset_name = parts[0]
                config_name = parts[1] if len(parts) > 1 else None
                iterator = iter_hf(dataset_name, config_name, "train", text_column, limit)
            elif src.startswith("hf:"):
                parts = src[3:].split("/", 1)
                dataset_name = parts[0]
                config_name = parts[1] if len(parts) > 1 else None
                iterator = iter_hf(dataset_name, config_name, "train", text_column, limit)
            else:
                ext = Path(src).suffix.lower()
                if ext == ".parquet" or ext == ".pq":
                    iterator = iter_parquet(src, text_column)
                else:
                    iterator = iter_jsonl(src)

            for text in iterator:
                if clean:
                    text = clean_text(text)
                if filter_quality(text):
                    yield text
                    count += 1
                    if limit is not None and count >= limit:
                        return

    texts = list(_source_iter())

    if deduplicate_texts:
        texts = deduplicate(texts)

    fmt_lower = fmt.lower()
    if fmt_lower == "jsonl":
        with open(output_path, "w", encoding="utf-8") as f:
            for text in texts:
                f.write(json.dumps({"text": text}) + "\n")
    elif fmt_lower == "txt":
        with open(output_path, "w", encoding="utf-8") as f:
            for text in texts:
                f.write(text + "\n\n")
    else:
        raise ValueError(f"Unsupported output format: {fmt}")

    print(f"Wrote {len(texts)} documents to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Prepare datasets for tokenizer/model training")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--sources", nargs="+", required=True, help="Input sources: file paths or hf://dataset/config")
    parser.add_argument("--format", choices=["jsonl", "txt"], default="jsonl", help="Output format")
    parser.add_argument("--text-column", default="text", help="Text column for Parquet/HuggingFace datasets")
    parser.add_argument("--no-deduplicate", action="store_true", help="Skip deduplication")
    parser.add_argument("--no-clean", action="store_true", help="Skip cleaning")
    parser.add_argument("--limit", type=int, default=None, help="Max documents to process")
    args = parser.parse_args()

    prepare(
        sources=args.sources,
        output_path=args.output,
        fmt=args.format,
        text_column=args.text_column,
        deduplicate_texts=not args.no_deduplicate,
        clean=not args.no_clean,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
