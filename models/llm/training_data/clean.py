import re
import os
import unicodedata
from typing import List, Optional


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_control_chars(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n\t")


def remove_urls(text: str) -> str:
    return re.sub(r"https?://\S+|www\.\S+", "", text)


def remove_emails(text: str) -> str:
    return re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "", text)


def remove_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def remove_markdown_artifacts(text: str) -> str:
    text = re.sub(r"\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"#{1,6}\s", "", text)
    text = re.sub(r"[-*_]{3,}", "", text)
    return text


def filter_short_lines(text: str, min_len: int = 20) -> str:
    return "\n".join(line for line in text.split("\n") if len(line.strip()) >= min_len)


def clean_text(text: str, min_len: int = 20) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = remove_control_chars(text)
    text = remove_urls(text)
    text = remove_emails(text)
    text = remove_html_tags(text)
    text = remove_markdown_artifacts(text)
    text = normalize_whitespace(text)
    text = filter_short_lines(text, min_len=min_len)
    return text.strip()


def clean_file(input_path: str, output_path: Optional[str] = None, min_len: int = 20, encoding: str = "utf-8") -> str:
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_clean{ext}"
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(input_path, "r", encoding=encoding) as fin, open(output_path, "w", encoding=encoding) as fout:
        for line in fin:
            cleaned = clean_text(line, min_len=min_len)
            if cleaned:
                fout.write(cleaned + "\n")
    return output_path


def clean_files(input_paths: List[str], output_dir: str, min_len: int = 20, encoding: str = "utf-8") -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    out_paths = []
    for path in input_paths:
        name = os.path.basename(path)
        out_path = os.path.join(output_dir, f"clean_{name}")
        clean_file(path, output_path=out_path, min_len=min_len, encoding=encoding)
        out_paths.append(out_path)
    return out_paths
