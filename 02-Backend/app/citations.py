import json
import os
from datetime import datetime
from .database import get_db

def get_sources(request_id: str, user_id: str) -> list[dict]:
    return [{"type": "memory", "confidence": 0.9}, {"type": "knowledge", "confidence": 0.85}]

def create_citation(source: dict, content: str) -> dict:
    return {"source": source, "content": content, "confidence": source.get("confidence", 0.0)}
