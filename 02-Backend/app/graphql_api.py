"""GraphQL API schema and resolvers."""

from typing import Any, Optional, List
from datetime import datetime

import strawberry
from strawberry import type, field, mutation, query, input
from strawberry.asgi import GraphQL
from fastapi import APIRouter

from app.multi_agent import agent_orchestrator, AgentRole
from app.evaluation.benchmark_suite import benchmark_suite
from app.evaluation.regression_testing import regression_suite
from app.safety.jailbreak import jailbreak_detector
from app.safety.input_moderation import input_moderator
from app.enterprise.service import OrganizationService
from app.enterprise.team_permissions import permission_manager

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
class AgentInfo:
    name: str
    role: str
    state: str
    capabilities: List[str]


@type
class EvaluationResult:
    suite: str
    accuracy: float
    passed: int
    failed: int


@type
class SafetyResult:
    safe: bool
    categories: List[str]
    confidence: float


@type
class Organization:
    id: str
    name: str
    plan: str
    member_count: int


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

    @field
    async def agents(self) -> List[AgentInfo]:
        analytics = agent_orchestrator.get_analytics()
        agents = analytics.get("agents", [])
        return [
            AgentInfo(
                name=a.get("name", ""),
                role=a.get("role", ""),
                state=a.get("state", ""),
                capabilities=a.get("capabilities", []),
            )
            for a in agents
        ]

    @field
    async def evaluation_benchmarks(self) -> List[str]:
        return benchmark_suite.list_benchmarks()

    @field
    async def organizations(self, user_id: Optional[str] = None) -> List[Organization]:
        if not user_id:
            return []
        service = OrganizationService()
        orgs = service.get_user_organizations(user_id)
        return [
            Organization(
                id=o.id,
                name=o.name,
                plan=getattr(o, "plan", "free"),
                member_count=getattr(o, "member_count", 0),
            )
            for o in orgs
        ]


@type
class Mutation:
    @mutation
    async def send_message(self, conversation_id: str, content: str) -> Message:
        return Message(id="1", content=content, role="user", created_at=datetime.utcnow())

    @mutation
    async def create_conversation(self, title: str) -> Conversation:
        return Conversation(id="1", title=title, messages=[], created_at=datetime.utcnow())

    @mutation
    async def run_benchmark(self, name: str, prompt: str) -> EvaluationResult:
        def model_func(p):
            return f"[result for {p}]"
        def grader_func(output, expected):
            return 0.8
        result = benchmark_suite.run(name, model_func, grader_func)
        return EvaluationResult(suite=result.benchmark_name, accuracy=result.accuracy, passed=result.passed, failed=result.failed)

    @mutation
    async def check_jailbreak(self, text: str) -> SafetyResult:
        results = jailbreak_detector.scan(text)
        safe = len(results) == 0
        categories = list({r.category for r in results})
        confidence = 1.0 if results else 0.0
        return SafetyResult(safe=safe, categories=categories, confidence=confidence)

    @mutation
    async def moderate_input(self, text: str) -> SafetyResult:
        result = input_moderator.moderate(text)
        return SafetyResult(safe=result.safe, categories=result.categories, confidence=result.confidence)


@input
class SendMessageInput:
    conversation_id: str
    content: str


@input
class CreateConversationInput:
    title: str


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQL(schema)
