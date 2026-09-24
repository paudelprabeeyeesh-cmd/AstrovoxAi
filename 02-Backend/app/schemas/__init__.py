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
    model: str = "gpt-4"
    pinned: bool = False
    archived: bool = False
    folder: str | None = None
    created_at: datetime
    updated_at: datetime
    memory_type: str | None = None
    importance_score: float = 0.5


class ConversationUpdate(BaseModel):
    title: str | None = None
    model: str | None = None
    pinned: bool | None = None
    archived: bool | None = None
    folder: str | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    model_used: str | None = None
    tokens_used: int | None = None
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
    updated_at: datetime
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
    properties: dict[str, Any] = Field(default_factory=dict)


class TrackEventRequest(BaseModel):
    event_name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None


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



class FineTuningExportRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    limit: int = Field(5000, ge=1, le=50000)


class FineTuningJobCreate(BaseModel):
    model: str = Field("gpt-4o-mini", min_length=1)
    training_file: str = Field(..., min_length=1)
    validation_file: str | None = None


class FineTuningJobStatus(BaseModel):
    id: str
    status: str
    model: str
    fine_tuned_model: str | None
    created_at: datetime
    finished_at: datetime | None
    trained_tokens: int | None


class FineTuningDeployRequest(BaseModel):
    job_id: str = Field(..., min_length=1)

class KnowledgeEntityCreate(BaseModel):
    entity_type: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    properties: dict[str, Any] = {}


class KnowledgeEntityOut(BaseModel):
    id: str
    entity_type: str
    name: str
    properties: dict[str, Any]
    created_at: datetime


class KnowledgeRelationshipCreate(BaseModel):
    source_name: str = Field(..., max_length=200)
    target_name: str = Field(..., max_length=200)
    relationship_type: str = Field(..., max_length=100)
    properties: dict[str, Any] = {}


class KnowledgeRelationshipOut(BaseModel):
    id: str
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relationship_type: str
    properties: dict[str, Any]
    created_at: datetime


class KnowledgeConnectionOut(BaseModel):
    id: str
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relationship_type: str
    created_at: datetime

class LocalGenerateRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=200)
    prompt: str = Field(..., min_length=1, max_length=10000)
    system: str = Field("", max_length=4000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=1, le=32768)
    stream: bool = False
    host: str = Field("", max_length=500)


class LocalGenerateResponse(BaseModel):
    result: str
    provider: str
    model: str


class LocalModelInfo(BaseModel):
    name: str
    provider: str
    host: str
    available: bool


class LocalPullRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=200)
    host: str = Field("", max_length=500)


class LocalPullResponse(BaseModel):
    success: bool
    message: str


class BatchJobCreate(BaseModel):
    inputs: list[dict[str, Any]]


class BatchJobOut(BaseModel):
    id: str
    user_id: str
    status: str
    input_data: str
    output_data: str | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class EmbeddingRequest(BaseModel):
    texts: list[str] | str
    model: str | None = "text-embedding-3-small"


class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]]
    model: str
    dimensions: int


class StructuredOutputRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    schema_json: dict[str, Any]
    model: str | None = None


class StructuredOutputResponse(BaseModel):
    data: dict[str, Any]
    model: str


class CitationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    sources: list[str]


class CitationResponse(BaseModel):
    citations: list[dict[str, Any]]


class AgentSkillCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field(..., max_length=2000)
    version: str = Field("1.0.0", max_length=50)
    tools: list[str] = []
    prompts: dict[str, Any] | None = None


class AgentSkillOut(BaseModel):
    id: str
    name: str
    description: str
    version: str
    tools: list[str]
    created_at: datetime


class AdminStatsResponse(BaseModel):
    total_users: int
    total_conversations: int
    total_messages: int
    total_api_calls: int
    total_cost_usd: float
    active_users_24h: int


class UsageResponse(BaseModel):
    user_id: str
    period: str
    api_calls: int
    tokens_used: int
    cost_usd: float
    by_model: dict[str, Any]


class TrainingDatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    file: bytes | None = None
    filename: str | None = Field(None, max_length=500)
    content_type: str | None = Field(None, max_length=100)


class TrainingDatasetOut(BaseModel):
    id: str
    user_id: str
    name: str
    filename: str
    content_type: str
    size: int
    path: str
    status: str
    created_at: datetime


class TrainingJobCreate(BaseModel):
    model: str = Field(..., min_length=1)
    training_file: str = Field(..., min_length=1)
    validation_file: str | None = None
    hyperparameters: dict[str, Any] | None = None


class TrainingJobOut(BaseModel):
    id: str
    user_id: str
    model: str
    training_file: str
    validation_file: str | None
    status: str
    fine_tuned_model: str | None
    created_at: datetime
    completed_at: datetime | None
    trained_tokens: int | None


class ModelRegistryEntryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    version: str = Field(..., min_length=1, max_length=50)
    provider: str = Field(..., min_length=1, max_length=100)
    model_id: str = Field(..., min_length=1, max_length=200)
    stage: str = Field("development", max_length=50)
    metadata: dict[str, Any] | None = None


class ModelRegistryEntryOut(BaseModel):
    id: str
    name: str
    version: str
    provider: str
    model_id: str
    stage: str
    metadata: dict[str, Any] | None
    created_at: datetime


class ModelDropdownItem(BaseModel):
    id: str
    name: str
    provider: str
    model_id: str
    stage: str
    source: str


class LongTermMemoryCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    category: str = Field("general", max_length=100)
    importance: float = Field(0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] | None = None


class LongTermMemoryOut(BaseModel):
    memory_id: str
    user_id: str
    content: str
    category: str
    importance: float
    tier: str
    created_at: datetime
    updated_at: datetime


class MemoryCompressionRequest(BaseModel):
    memories: list[dict[str, Any]]
    max_length: int | None = None


class MemoryCompressionResponse(BaseModel):
    compressed: list[dict[str, Any]]
    original_total_length: int
    compressed_total_length: int


class MemorySyncRequest(BaseModel):
    layers: dict[str, list[dict[str, Any]]]


class MemorySyncResponse(BaseModel):
    results: dict[str, Any]


class MemoryTimelineResponse(BaseModel):
    events: list[dict[str, Any]]


class UserMemoryProfileResponse(BaseModel):
    user_id: str
    preferences: dict[str, Any]
    personal_facts: dict[str, Any]
    workflows: dict[str, Any]
    goals: list[dict[str, Any]]
    last_updated: str


class KnowledgeBaseDocumentCreate(BaseModel):
    title: str = Field(..., max_length=500)
    content: str = Field(..., max_length=100000)
    doc_type: str = Field("text", max_length=50)
    metadata: dict[str, Any] | None = None


class KnowledgeBaseDocumentOut(BaseModel):
    doc_id: str
    user_id: str
    title: str
    content: str
    doc_type: str
    metadata: dict[str, Any]
    created_at: datetime


class IncrementalIndexStatsResponse(BaseModel):
    version: int
    total_documents: int
    pending_additions: int
    pending_deletions: int


class SemanticRetrievalResponse(BaseModel):
    results: list[dict[str, Any]]
    query: str
    total: int


class AudioTranscriptionRequest(BaseModel):
    file_path: str = Field(..., max_length=1000)
    model: str = Field("base", max_length=50)


class AudioTranscriptionResponse(BaseModel):
    text: str
    model: str
    file_path: str


class VideoCaptionRequest(BaseModel):
    file_path: str = Field(..., max_length=1000)


class VideoCaptionResponse(BaseModel):
    captions: str
    file_path: str


class MemoryVisualizationTimelineResponse(BaseModel):
    events: list[dict[str, Any]]
    total: int


class MemoryLayerDistributionResponse(BaseModel):
    total: int
    distribution: dict[str, dict[str, Any]]


class MemoryHeatmapResponse(BaseModel):
    data: list[dict[str, Any]]


class MarketplaceListingCreate(BaseModel):
    listing_type: str = Field("prompt", max_length=50)
    title: str = Field(..., max_length=200)
    description: str = Field("", max_length=2000)
    content: dict[str, Any] = {}
    price: float = Field(0.0, ge=0.0)
    tags: list[str] = []


class MarketplaceListingOut(BaseModel):
    listing_id: str
    listing_type: str
    title: str
    description: str
    price: float
    author_id: str
    downloads: int
    rating: float
    tags: list[str]
    created_at: datetime


class AIAppCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field("", max_length=2000)
    version: str = Field("1.0.0", max_length=50)
    manifest: dict[str, Any] = {}
    permissions: list[str] = []
    tags: list[str] = []


class AIAppOut(BaseModel):
    app_id: str
    name: str
    description: str
    version: str
    author_id: str
    status: str
    install_count: int
    rating: float
    tags: list[str]
    created_at: datetime


class CollaborationSessionCreate(BaseModel):
    name: str = Field(..., max_length=200)
    participants: list[str] = []


class CollaborationSessionOut(BaseModel):
    session_id: str
    name: str
    participants: list[str]
    status: str
    created_at: datetime


class TenantCreate(BaseModel):
    name: str = Field(..., max_length=200)
    plan: str = Field("free", max_length=50)
    owner_id: str


class TenantOut(BaseModel):
    tenant_id: str
    name: str
    slug: str
    plan: str
    status: str
    owner_id: str
    created_at: datetime


class FederatedRoundCreate(BaseModel):
    client_ids: list[str] = []
    global_model_version: str = Field("1.0.0", max_length=50)


class FederatedRoundOut(BaseModel):
    round_id: str
    global_model_version: str
    clients: list[str]
    updates_received: int
    status: str
    created_at: datetime


class SyntheticDatasetCreate(BaseModel):
    schema_name: str = Field(..., max_length=200)
    num_rows: int = Field(100, ge=1, le=100000)


class SyntheticDatasetOut(BaseModel):
    dataset_id: str
    name: str
    schema: dict[str, Any]
    rows: list[dict[str, Any]]
    generation_method: str
    created_at: datetime


class EvaluationSuiteCreate(BaseModel):
    name: str = Field(..., max_length=200)
    benchmarks: list[str] = []
    metrics: list[str] = []


class EvaluationSuiteOut(BaseModel):
    suite_id: str
    name: str
    description: str
    benchmarks: list[str]
    metrics: list[str]
    created_at: datetime


class EvaluationRunCreate(BaseModel):
    suite_id: str
    model_id: str
    model_version: str


class EvaluationRunOut(BaseModel):
    run_id: str
    suite_id: str
    model_id: str
    model_version: str
    status: str
    results: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None


class WebhookEventCreate(BaseModel):
    provider: str = Field(..., max_length=100)
    event_type: str = Field(..., max_length=100)
    payload: dict[str, Any] = {}
    headers: dict[str, str] = {}


class WebhookEventOut(BaseModel):
    event_id: str
    provider: str
    event_type: str
    processed: bool
    received_at: datetime


class EventOut(BaseModel):
    event_id: str
    event_type: str
    payload: dict[str, Any]
    priority: str
    timestamp: datetime


class QueuedMessageOut(BaseModel):
    message_id: str
    queue_name: str
    payload: dict[str, Any]
    status: str
    retries: int
    created_at: datetime

