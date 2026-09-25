import json
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_jsonl_format(file_path: str) -> list[str]:
    errors = []
    if not os.path.exists(file_path):
        return [f"File not found: {file_path}"]

    with open(file_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {lineno}: Invalid JSON - {e}")
                continue

            if not isinstance(entry, dict):
                errors.append(f"Line {lineno}: Entry must be a JSON object")
                continue

            if "messages" not in entry:
                errors.append(f"Line {lineno}: Missing 'messages' key")
                continue

            if not isinstance(entry["messages"], list):
                errors.append(f"Line {lineno}: 'messages' must be a list")
                continue

            if len(entry["messages"]) < 2:
                errors.append(f"Line {lineno}: Need at least 2 messages")

            for msg_idx, msg in enumerate(entry["messages"]):
                if not isinstance(msg, dict):
                    errors.append(f"Line {lineno}, message {msg_idx}: Must be an object")
                    continue
                if "role" not in msg:
                    errors.append(f"Line {lineno}, message {msg_idx}: Missing 'role'")
                if "content" not in msg:
                    errors.append(f"Line {lineno}, message {msg_idx}: Missing 'content'")

            if "metadata" in entry and not isinstance(entry["metadata"], dict):
                errors.append(f"Line {lineno}: 'metadata' must be a dict")

    return errors


def check_required_fields(records: list[dict]) -> list[str]:
    errors = []
    required_keys = {"messages"}
    for idx, record in enumerate(records, 1):
        missing = required_keys - set(record.keys())
        if missing:
            errors.append(f"Record {idx}: Missing required fields: {missing}")
        if "messages" in record:
            for msg_idx, msg in enumerate(record["messages"]):
                if not isinstance(msg, dict):
                    errors.append(f"Record {idx}, message {msg_idx}: Not a dict")
                    continue
                for field in ("role", "content"):
                    if field not in msg:
                        errors.append(f"Record {idx}, message {msg_idx}: Missing '{field}'")
    return errors


def validate_token_counts(records: list[dict], max_tokens: int = 8192) -> list[str]:
    errors = []
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o")
    except Exception:
        return ["tiktoken not available for token counting"]

    for idx, record in enumerate(records, 1):
        total = 0
        for msg in record.get("messages", []):
            if isinstance(msg, dict) and "content" in msg:
                total += len(enc.encode(msg["content"]))
        if total > max_tokens:
            errors.append(f"Record {idx}: Token count {total} exceeds max {max_tokens}")
    return errors


def generate_validation_report(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"valid": False, "errors": [f"File not found: {file_path}"], "record_count": 0}

    errors = validate_jsonl_format(file_path)

    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    field_errors = check_required_fields(records)
    token_errors = validate_token_counts(records)

    all_errors = errors + field_errors + token_errors

    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "record_count": len(records),
        "file_path": file_path,
    }
