"""Registry schemas for topic entries."""

from __future__ import annotations

from typing import Any

TOPIC_SCHEMA = {
    "id": "str",            # e.g. S1.T001
    "topic_number": "int",
    "section": "int",
    "section_name": "str",
    "level": "int",         # 0-5
    "name": "str",
    "status": "str",        # planned/scaffolded/implemented/tested/verified/blocked
    "domain": "str",
    "subdomain": "str",
    "prerequisites": "list[str]",
    "difficulty": "int",    # 1-5
    "implementation_module": "str",
    "operations": "list[str]",
    "dependencies": "list[str]",
    "ai_application": "str",
    "verified": "bool",
}

VALID_STATUSES = {"planned", "scaffolded", "implemented", "tested", "verified", "blocked"}
