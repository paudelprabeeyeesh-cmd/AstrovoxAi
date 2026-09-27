import re
import unicodedata


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def filter_quality(text: str, min_length: int = 40, max_length: int = 100_000, alpha_ratio: float = 0.5) -> bool:
    if not isinstance(text, str):
        return False
    if len(text) < min_length:
        return False
    if len(text) > max_length:
        return False
    if sum(c.isalpha() for c in text) / max(len(text), 1) < alpha_ratio:
        return False
    if text.count("http") > 20:
        return False
    return True


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = normalize_text(text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[^\x00-\x7F\u0080-\u00FF\u0100-\u017F\u2000-\u206F\u2190-\u21FF\u2200-\u22FF]", " ", text)
    text = re.sub(r"[^\w\s.,!?;:'\"\-\(\)\[\]\{\}]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_file(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    cleaned = clean_text(text)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned)
