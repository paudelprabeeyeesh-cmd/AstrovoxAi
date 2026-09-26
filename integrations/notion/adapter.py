"""Notion integration adapter."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class NotionAdapter:
    def __init__(self, token: str = ""):
        self.token = token
        self.base_url = "https://api.notion.com/v1"

    def search(self, query: str = "") -> list[dict]:
        return [
            {"id": "page-1", "title": "Project Notes", "url": "https://notion.so/page-1"},
            {"id": "page-2", "title": "Meeting Notes", "url": "https://notion.so/page-2"},
        ]

    def create_page(self, parent_id: str, title: str, content: str = "") -> dict:
        return {"id": "new-page", "title": title, "url": f"https://notion.so/new-page"}

    def append_block(self, page_id: str, block_type: str, content: str) -> dict:
        return {"page_id": page_id, "block_type": block_type, "content": content}


notion_adapter = NotionAdapter()
