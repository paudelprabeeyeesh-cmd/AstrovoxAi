import re
import unicodedata


def clean_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x00-\x7F\u0080-\u00FF\u0100-\u017F\u2000-\u206F\u2190-\u21FF\u2200-\u22FF]", " ", text)
    return text.strip()


def clean_file(input_path, output_path):
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    cleaned = clean_text(text)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned)
