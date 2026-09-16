from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    CONVERSATION = "conversation"
    LONG_TERM = "long_term"
    PROJECT = "project"

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
    memory_type: str | None = None
    importance_score: float = 0.5


class ConversationOut(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    memory_type: str | None = None
    importance_score: float = 0.5


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    memory_type: str | None = None
    importance_score: float = 0.5


class SolveRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    user_id: str | None = Field(None, min_length=1)
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
    suggestions: list[str] = []


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
    memory_type: str | None = None
    importance_score: float = 0.5


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
    memory_type: str | None = None
    importance_score: float = 0.5


class KnowledgeDocCreate(BaseModel):
    title: str | None = None
    content: str = Field(..., max_length=50000)


class KnowledgeDocOut(BaseModel):
    id: str
    title: str | None
    content: str
    created_at: datetime
    memory_type: str | None = None
    importance_score: float = 0.5


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
    memory_type: str | None = None
    importance_score: float = 0.5


class ToolCreate(BaseModel):
    type: str = Field(..., max_length=50)
    config: str = Field(..., max_length=4000)


class ToolOut(BaseModel):
    id: str
    type: str
    config: str
    created_at: datetime
    memory_type: str | None = None
    importance_score: float = 0.5


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
    memory_type: str | None = None
    importance_score: float = 0.5


class ConversationSearchOut(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    memory_type: str | None = None
    importance_score: float = 0.5
    message_count: int


class ConsentRecord(BaseModel):
    consent_type: str
    granted: bool


class GenUIResponse(BaseModel):
    type: str = Field(..., max_length=50)
    data: dict[str, Any]


class AnalyticsEventCreate(BaseModel):
    event_type: str = Field(..., max_length=100)
    properties: dict[str, Any] = {}


class AnalyticsAggregateOut(BaseModel):
    window_days: int
    generated_at: str
    events: list[dict[str, Any]]


class RAGEvalCreate(BaseModel):
    query: str = Field(..., max_length=10000)
    retrieved_ids: list[str] = []
    golden_ids: list[str] = []
    faithfulness_score: float = Field(..., ge=0.0, le=1.0)
    metadata: dict[str, Any] | None = None


class RAGEvalOut(BaseModel):
    id: str
    query: str
    recall_at_5: float
    faithfulness_score: float
    created_at: datetime
    memory_type: str | None = None
    importance_score: float = 0.5


class ExperimentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    hypothesis: str = Field(..., max_length=500)
    variants: list[str] = Field(..., max_length=10)
    traffic_split: list[float] = Field(..., max_length=10)


class ExperimentOut(BaseModel):
    id: str
    name: str
    hypothesis: str
    variants: list[str]
    status: str
    created_at: datetime
    memory_type: str | None = None
    importance_score: float = 0.5


class ExperimentResultOut(BaseModel):
    variant: str
    metric: str
    avg_value: float
    samples: int

class DocumentOut(BaseModel):
    id: str
    user_id: str
    filename: str
    content_type: str
    size: int
    created_at: datetime


class DocumentChunkOut(BaseModel):
    id: str
    document_id: str
    content: str
    metadata: dict[str, Any] | None = None
    created_at: datetime


class RAGSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    filename: str
    metadata: dict[str, Any] | None = None
    score: float


class RAGIngestResponse(BaseModel):
    doc_id: str
    chunks: int


class RAGIngestRequest(BaseModel):
    url: str = Field(..., max_length=2000)
    user_id: str | None = None


class RAGGithubRequest(BaseModel):
    repo_url: str = Field(..., max_length=500)
    user_id: str | None = None

class ToolExecuteRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    max_iterations: int = Field(5, ge=1, le=10)


class SearchResultOut(BaseModel):
    id: str
    content: str
    score: float
    metadata: dict[str, Any] | None = None
    source: str


class MemoryClassifyRequest(BaseModel):
    memory_id: str
    categories: list[str] | None = None


class MemoryClassifyResponse(BaseModel):
    memory_id: str
    category: str
    confidence: float


class ToolExecuteResponse(BaseModel):
    result: str


class SecurityScanPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)


class SecurityScanPromptResponse(BaseModel):
    injected: bool
    confidence: float


class SecurityScanSecretsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)


class SecurityScanSecretsResponse(BaseModel):
    secrets_found: int
    findings: list[dict]


class AuditLogRequest(BaseModel):
    action: str
    resource: str = ""
    details: dict | None = None


class AuditLogResponse(BaseModel):
    success: bool
    entry_id: str


class AuditLogsResponse(BaseModel):
    logs: list[dict]
    total: int


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    scopes: str = "read"


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    key: str
    scopes: str
    created_at: datetime


class ApiKeyRevokeRequest(BaseModel):
    key_id: str

