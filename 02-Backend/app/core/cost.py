import tiktoken
from typing import Optional

MODEL_TOKENIZERS = {
    "gpt-4o-mini-2024-07-18": "o200k_base",
    "gpt-4o-2024-08-06": "o200k_base",
    "gpt-4-turbo-2024-04-09": "cl100k_base",
    "gpt-4-0125-preview": "cl100k_base",
    "claude-3-5-sonnet-20240620": "cl100k_base",
    "gemini-1.5-pro": "o200k_base",
}


def get_tokenizer(model: str):
    encoding_name = MODEL_TOKENIZERS.get(model, "cl100k_base")
    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-4o-mini-2024-07-18") -> int:
    tokenizer = get_tokenizer(model)
    return len(tokenizer.encode(text))


def estimate_cost(tokens: int, model: str = "gpt-4o-mini-2024-07-18") -> float:
    cost_per_1k = {
        "gpt-4o-mini-2024-07-18": 0.00015,
        "gpt-4o-2024-08-06": 0.005,
        "gpt-4-turbo-2024-04-09": 0.01,
        "gpt-4-0125-preview": 0.01,
        "claude-3-5-sonnet-20240620": 0.003,
        "gemini-1.5-pro": 0.00125,
    }
    rate = cost_per_1k.get(model, 0.001)
    return (tokens / 1000) * rate
