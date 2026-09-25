"""GraphQL API schema and resolvers."""

from typing import Any, Optional, List
from datetime import datetime

import strawberry
from strawberry import type, field, mutation, query, input
from strawberry.asgi import GraphQL
from fastapi import APIRouter

router = APIRouter()


@type
class Message:
    id: str
    content: str
    role: str
    created_at: datetime


@type
class Conversation:
    id: str
    title: str
    messages: List[Message]
    created_at: datetime


@type
class Query:
    @field
    async def health(self) -> str:
        return "ok"

    @field
    async def conversation(self, id: str) -> Optional[Conversation]:
        return None

    @field
    async def conversations(self, limit: int = 10) -> List[Conversation]:
        return []


@type
class Mutation:
    @mutation
    async def send_message(self, conversation_id: str, content: str) -> Message:
        return Message(id="1", content=content, role="user", created_at=datetime.utcnow())

    @mutation
    async def create_conversation(self, title: str) -> Conversation:
        return Conversation(
            id="1", title=title, messages=[], created_at=datetime.utcnow()
        )


@input
class SendMessageInput:
    conversation_id: str
    content: str


@input
class CreateConversationInput:
    title: str


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQL(schema)
