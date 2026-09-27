#!/usr/bin/env python3
"""CLI benchmark harness for tokenizer research variants.

Compares all registered tokenizer implementations on a shared corpus,
emits a JSON results file and an optional markdown report.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.llm.tokenizer.research import (  # noqa: E402
    AdaptiveTokenizer,
    BaseTokenizer,
    BenchmarkResult,
    BPETokenizer,
    ByteTokenizer,
    CharacterTokenizer,
    CompressionAnalyzer,
    ContextUtilizationBenchmark,
    CrossLanguageBenchmark,
    DynamicVocabulary,
    OnlineTokenizerUpdater,
    OOVAnalyzer,
    SentencePieceTokenizer,
    SpeedBenchmark,
    TokenEfficiencyBenchmark,
    UnigramTokenizer,
    VocabularyMerger,
    VocabularyPruner,
    WordPieceTokenizer,
    train_bpe_tokenizer,
    train_wordpiece_tokenizer,
)

# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------
SAMPLE_TEXTS = [
    "Hello world! This is a test of the tokenizer research module.",
    "The quick brown fox jumps over the lazy dog.",
    "In computer science, a tokenizer is a program that breaks a stream of text into words, symbols, or other meaningful elements called tokens.",
    "Machine learning models process text as sequences of tokens. The choice of tokenizer affects model performance, context utilization, and inference speed.",
    "Bonjour le monde! Ceci est un test du module de recherche sur les tokenizers.",
    "Hola mundo! Esta es una prueba del m\u00f3dulo de investigaci\u00f3n de tokenizadores.",
    "Guten Tag! Dies ist ein Test des Tokenizer-Forschungsmoduls.",
    "0123456789\n\t\r Special characters: !@#$%^&*()_+-=[]{}|;:',.<>?/~`",
    "Mixed language content: English + Fran\u00e7ais + Espa\u00f1ol + Deutsch + \u4e2d\u6587",
    "Repeated token stress test: token token token token token token token token token token.",
]


CROSS_LANG_SAMPLES: dict[str, list[str]] = {
    "en": ["Hello world", "Machine learning", "Natural language processing"],
    "fr": ["Bonjour le monde", "L'apprentissage automatique", "Traitement du langage naturel"],
    "es": ["Hola mundo", "Aprendizaje autom\u00e1tico", "Procesamiento del lenguaje natural"],
    "de": ["Hallo Welt", "Maschinelles Lernen", "Nat\u00fcrliche Sprachverarbeitung"],
    "zh": ["\u4f60\u597d\u4e16\u754c", "\u673a\u5668\u5b66\u4e60", "\u81ea\u7136\u8bed\u8a00\u5904\u7406"],
}


# ---------------------------------------------------------------------------
# Tokenizer builders
# ---------------------------------------------------------------------------
def _build_bpe() -> BPETokenizer | None:
    try:
        tokenizer = train_bpe_tokenizer(
            SAMPLE_TEXTS,
            vocab_size=1000,
            min_frequency=1,
            special_tokens=["<s>", "<pad>", "</s>", "<unk>"],
        )
        return tokenizer
    except Exception as exc:
        print(f"[warn] BPE training failed: {exc}")
        return None


def _build_wordpiece() -> WordPieceTokenizer | None:
    try:
        tokenizer = train_wordpiece_tokenizer(
            SAMPLE_TEXTS,
            vocab_size=1000,
            min_frequency=1,
            special_tokens=["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]"],
        )
        return tokenizer
    except Exception as exc:
        print(f"[warn] WordPiece training failed: {exc}")
        return None


def _build_sentencepiece() -> SentencePieceTokenizer | None:
    try:
        from models.llm.tokenizer.research import train_sentencepiece_model
        prefix = os.path.join(os.path.dirname(__file__), "..", "sp_benchmark_model")
        tokenizer = train_sentencepiece_model(SAMPLE_TEXTS, model_prefix=prefix, vocab_size=1000, model_type="bpe")
        return tokenizer
    except Exception as exc:
        print(f"[warn] SentencePiece training failed: {exc}")
        return None


def _build_unigram() -> UnigramTokenizer | None:
    try:
        vocab = {tok: i for i, tok in enumerate(set("".join(SAMPLE_TEXTS)))}
        return UnigramTokenizer(vocab={tok: float(i) for tok, i in vocab.items()})
    except Exception as exc:
        print(f"[warn] Unigram init failed: {exc}")
        return None


def _build_byte() -> ByteTokenizer | None:
    try:
        return ByteTokenizer()
    except Exception as exc:
        print(f"[warn] Byte tokenizer init failed: {exc}")
        return None


def _build_character() -> CharacterTokenizer | None:
    try:
        tok = CharacterTokenizer()
        for ch in set("".join(SAMPLE_TEXTS)):
            tok.encode(ch)
        return tok
    except Exception as exc:
        print(f"[warn] Character tokenizer init failed: {exc}")
        return None


def _build_adaptive(base: BaseTokenizer) -> AdaptiveTokenizer | None:
    try:
        return AdaptiveTokenizer(base_tokenizer=base)
    except Exception as exc:
        print(f"[warn] Adaptive tokenizer init failed: {exc}")
        return None


def _build_online(base: BaseTokenizer) -> tuple[OnlineTokenizerUpdater | None, list[str]]:
    try:
        updater = OnlineTokenizerUpdater(tokenizer=base, buffer_size=1000)
        return updater, SAMPLE_TEXTS[:5]
    except Exception as exc:
        print(f"[warn] Online updater init failed: {exc}")
        return None, []


# ---------------------------------------------------------------------------
# Benchmark execution
# ---------------------------------------------------------------------------
def run_suite(tokenizer_name: str, tokenizer: Any, texts: list[str]) -> dict[str, Any]:
    results: dict[str, Any] = {"name": tokenizer_name}
    try:
        speed = SpeedBenchmark.run(tokenizer, texts, warmup=5)
        results["speed"] = speed.to_dict()
        results["speed_samples"] = [
            {"text": s.text[:80], "tokens": s.num_tokens, "ms": round(s.encoding_time_ms, 4)} for s in speed.samples
        ]
    except Exception as exc:
        results["speed_error"] = str(exc)
    try:
        ctx = ContextUtilizationBenchmark.run(tokenizer, texts, context_length=2048)
        results["context_utilization"] = ctx.to_dict()
    except Exception as exc:
        results["context_utilization_error"] = str(exc)
    try:
        eff = TokenEfficiencyBenchmark.run(tokenizer, texts)
        results["token_efficiency"] = eff.to_dict()
    except Exception as exc:
        results["token_efficiency_error"] = str(exc)
    try:
        cross = CrossLanguageBenchmark.run(tokenizer, CROSS_LANG_SAMPLES)
        results["cross_language"] = cross.to_dict()
    except Exception as exc:
        results["cross_language_error"] = str(exc)
    try:
        comp = CompressionAnalyzer.analyze(tokenizer, texts)
        results["compression"] = comp
    except Exception as exc:
        results["compression_error"] = str(exc)
    try:
        oov = OOVAnalyzer.analyze(tokenizer, texts)
        results["oov"] = oov
    except Exception as exc:
        results["oov_error"] = str(exc)
    return results


def run_vocab_operations(texts: list[str]) -> dict[str, Any]:
    ops: dict[str, Any] = {}
    tokens = [tok for text in texts for tok in _build_bpe().encode(text).tokens]
    try:
        vocab = DynamicVocabulary(max_size=5000)
        vocab.add_many(tokens)
        removed = vocab.prune_by_frequency(tokens, min_count=2)
        ops["dynamic_vocab"] = {
            "size": vocab._next_id,
            "pruned": removed,
        }
        vocab.save(os.path.join(os.path.dirname(__file__), "..", "dynamic_vocab_bench"))
    except Exception as exc:
        ops["dynamic_vocab_error"] = str(exc)
    try:
        pruner = VocabularyPruner()
        base = _build_bpe()
        if base is not None:
            new_vocab, removed = pruner.prune(base, tokens, min_count=2)
            ops["pruning"] = {"new_vocab_size": len(new_vocab), "removed": removed}
        else:
            ops["pruning_error"] = "base tokenizer unavailable"
    except Exception as exc:
        ops["pruning_error"] = str(exc)
    try:
        source = {"hello": 0, "world": 1, "foo": 2}
        target = {"foo": 0, "bar": 1, "baz": 2}
        merged = VocabularyMerger.merge(source, target, strategy="keep")
        ops["merging"] = {"merged_size": len(merged), "sample": list(merged.items())[:5]}
    except Exception as exc:
        ops["merging_error"] = str(exc)
    try:
        base = _build_bpe()
        updater, short_texts = _build_online(base) if base is not None else (None, [])
        if updater is not None:
            for t in short_texts:
                updater.ingest(t)
            added = updater.flush()
            ops["online_update"] = {"added": added, "final_vocab_size": updater.tokenizer.vocab_size()}
        else:
            ops["online_update_error"] = "base tokenizer unavailable"
    except Exception as exc:
        ops["online_update_error"] = str(exc)
    return ops


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark tokenizer research variants.")
    parser.add_argument("--output", default="benchmark_results/tokenizer_benchmark.json", help="Output JSON path")
    parser.add_argument("--markdown", default=None, help="Optional markdown report path")
    parser.add_argument("--tokenizers", nargs="*", default=None, help="Subset of tokenizer names to run")
    parser.add_argument("--warmup", type=int, default=5, help="Warmup iterations for speed benchmark")
    args = parser.parse_args(argv)

    texts = SAMPLE_TEXTS
    builders: dict[str, Callable[[], Any]] = {
        "bpe": _build_bpe,
        "wordpiece": _build_wordpiece,
        "sentencepiece": _build_sentencepiece,
        "unigram": _build_unigram,
        "byte": _build_byte,
        "character": _build_character,
    }

    selected = args.tokenizers
    if selected is not None:
        unknown = [n for n in selected if n not in builders]
        if unknown:
            parser.error(f"Unknown tokenizer names: {unknown}")
        builders = {k: v for k, v in builders.items() if k in selected}

    print("Building tokenizers...")
    tokenizers: dict[str, Any] = {}
    for name, builder in builders.items():
        instance = builder()
        if instance is not None:
            tokenizers[name] = instance
            print(f"  [ok] {name} vocab_size={instance.vocab_size()}")
        else:
            print(f"  [skip] {name}")

    if not tokenizers:
        print("No tokenizers available. Install huggingface tokenizers and/or sentencepiece.")
        return 1

    print("\nRunning benchmarks...")
    suite: dict[str, Any] = {"tokenizers": {}}
    for name, tok in tokenizers.items():
        print(f"  -> {name}")
        suite["tokenizers"][name] = run_suite(name, tok, texts)
        if "speed" in suite["tokenizers"][name]:
            spd = suite["tokenizers"][name]["speed"]
            print(f"     speed: {spd['tokens_per_second']:.2f} tok/s")
        if "compression" in suite["tokenizers"][name]:
            comp = suite["tokenizers"][name]["compression"]
            print(f"     compression: {comp['compression_ratio']:.4f}")

    print("\nRunning vocabulary operations...")
    suite["vocabulary_operations"] = run_vocab_operations(texts)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(suite, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResults saved to: {out_path}")

    if args.markdown:
        from models.llm.tokenizer.research import generate_comparison_markdown
        results_for_md = [
            BenchmarkResult(
                name=data["name"],
                samples=[],
                metadata={k: v for k, v in data.items() if k != "name" and k != "speed_samples"},
            )
            for data in suite["tokenizers"].values()
            if "speed" in data
        ]
        md = generate_comparison_markdown(results_for_md)
        Path(args.markdown).write_text(md, encoding="utf-8")
        print(f"Markdown report saved to: {args.markdown}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
