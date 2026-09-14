from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class MemoryCreate(BaseModel):
    key: str = Field(..., max_length=200)
    value: str = Field(..., max_length=4000)


class MemoryUpdate(BaseModel):
    value: str = Field(..., max_length=4000)


class MemoryOut(BaseModel):
    id: str
    key: str
    value: str
    created_at: datetime


class ConversationOut(BaseModel):
    id: str
    title: str | None
    created_at: datetime


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class SolveRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    user_id: str = Field(..., min_length=1)
    conversation_id: str | None = None


class SolveResponse(BaseModel):
    result: str
    provider: str
    model: str
    cost_usd: float
    cached: bool
    memories_used: list[str] = []
    conversation_id: str | None = None
    message_id: str | None = None
    confidence: float = 0.0
    refused: bool = False


class TemplateCreate(BaseModel):
    name: str = Field(..., max_length=200)
    prompt: str = Field(..., max_length=10000)
    variables: str | None = None


class TemplateOut(BaseModel):
    id: str
    name: str
    prompt: str
    variables: str | None
    created_at: datetime


class ScheduleCreate(BaseModel):
    template_id: str | None = None
    cron: str = Field(..., max_length=100)
    email: EmailStr


class ScheduleOut(BaseModel):
    id: str
    template_id: str | None
    cron: str
    email: str
    last_run: datetime | None
    active: bool
    created_at: datetime


class KnowledgeDocCreate(BaseModel):
    title: str | None = None
    content: str = Field(..., max_length=50000)


class KnowledgeDocOut(BaseModel):
    id: str
    title: str | None
    content: str
    created_at: datetime


class UserProfileOut(BaseModel):
    user_id: str
    style_json: str | None
    updated_at: datetime


class WorkflowCreate(BaseModel):
    name: str = Field(..., max_length=200)
    steps: str = Field(..., max_length=50000)


class WorkflowOut(BaseModel):
    id: str
    name: str
    steps: str
    created_at: datetime


class ToolCreate(BaseModel):
    type: str = Field(..., max_length=50)
    config: str = Field(..., max_length=4000)


class ToolOut(BaseModel):
    id: str
    type: str
    config: str
    created_at: datetime


class FeedbackCreate(BaseModel):
    request_id: str | None = None
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


class FeedbackOut(BaseModel):
    id: str
    request_id: str | None
    rating: int
    comment: str | None
    created_at: datetime


class ConversationSearchOut(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    message_count: int
