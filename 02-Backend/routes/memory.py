from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import os

router = APIRouter()

class MemoryItem(BaseModel):
    key: str
    value: str

class MemoryResponse(BaseModel):
    memory: List[dict]

# Simple in-memory store (replace with database in production)
memory_store = {}

@router.get("/{user_id}")
async def get_memory(user_id: str):
    return {"memory": memory_store.get(user_id, [])}

@router.post("/")
async def save_memory(user_id: str, key: str, value: str):
    if user_id not in memory_store:
        memory_store[user_id] = []
    memory_store[user_id].append({"key": key, "value": value, "timestamp": __import__('datetime').datetime.now().isoformat()})
    return {"success": True}

@router.delete("/{user_id}")
async def clear_memory(user_id: str):
    if user_id in memory_store:
        memory_store[user_id] = []
    return {"success": True}