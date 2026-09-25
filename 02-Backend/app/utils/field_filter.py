"""Field filtering and partial response support."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def filter_fields(data: Any, fields: Optional[List[str]]) -> Any:
    if fields is None:
        return data
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in set(fields)}
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return [filter_fields(item, fields) for item in data]
    return data


def parse_fields(header: Optional[str]) -> Optional[List[str]]:
    if not header:
        return None
    return [f.strip() for f in header.split(",") if f.strip()]


def sparse_field_response(data: Any, fields_param: Optional[str]) -> Any:
    fields = parse_fields(fields_param)
    if not fields:
        return data
    return filter_fields(data, fields)
