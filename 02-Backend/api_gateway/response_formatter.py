import json
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class FormattedResponse:
    status_code: int
    body: Dict[str, Any]
    headers: Dict[str, str]
    raw: str


class ResponseFormatter:
    def __init__(self, indent: int = 2, content_type: str = "application/json"):
        self._indent = indent
        self._content_type = content_type

    def format_success(
        self,
        data: Any,
        message: str = "OK",
        status_code: int = 200,
        request_id: str = "",
    ) -> FormattedResponse:
        body: Dict[str, Any] = {"success": True, "message": message, "data": data}
        if request_id:
            body["request_id"] = request_id
        return self._build(body, status_code)

    def format_error(
        self,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        request_id: str = "",
    ) -> FormattedResponse:
        body: Dict[str, Any] = {"success": False, "message": message}
        if details:
            body["errors"] = details
        if request_id:
            body["request_id"] = request_id
        return self._build(body, status_code)

    def format_paginated(
        self,
        data: list,
        page: int,
        page_size: int,
        total: int,
        request_id: str = "",
    ) -> FormattedResponse:
        body: Dict[str, Any] = {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
            },
        }
        if request_id:
            body["request_id"] = request_id
        return self._build(body, 200)

    def _build(self, body: Dict[str, Any], status_code: int) -> FormattedResponse:
        raw = json.dumps(body, indent=self._indent)
        headers = {"Content-Type": self._content_type}
        return FormattedResponse(
            status_code=status_code,
            body=body,
            headers=headers,
            raw=raw,
        )
