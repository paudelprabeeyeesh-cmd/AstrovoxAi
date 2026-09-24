"""
Intelligence Core - Phase 2.1

The central orchestration layer that coordinates all intelligence components:
- Memory Engine
- Planning Engine
- Tool Engine
- Model Orchestration
- Response Generation
- Cost Optimization
- Execution Tracing
- Reliability Safeguards
- Context Compression
- Self-Correction Loop
"""

from typing import Any, Dict, List, Optional
import uuid

from .model_orchestrator import ModelOrchestrator, TaskType
from .prompt_engine import PromptEngine, ContextSource
from .reasoning_pipeline import ReasoningPipeline
from .tool_engine import ToolEngine
from .planning_engine import PlanningEngine
from .response_generator import ResponseGenerator, ResponseFormat
from .cost_optimizer import CostOptimizer
from .execution_tracer import ExecutionTracer, TraceEventType
from .reliability import ReliabilitySafeguards
from app.model_router_v2 import MultiModelRouter, RoutingRequest, RoutingPolicy, FallbackStrategy
from app.context_compression import ContextCompressor, CompressionStrategy
from app.self_correction import SelfCorrectionLoop
from app.thinking import get_thinking_config


class IntelligenceCore:
    def __init__(self):
        self.model_orchestrator = ModelOrchestrator()
        self.prompt_engine = PromptEngine()
        self.reasoning_pipeline = ReasoningPipeline()
        self.tool_engine = ToolEngine()
        self.planning_engine = PlanningEngine()
        self.response_generator = ResponseGenerator()
        self.cost_optimizer = CostOptimizer()
        self.execution_tracer = ExecutionTracer()
        self.reliability = ReliabilitySafeguards()
        self.multi_model_router = MultiModelRouter(orchestrator=self.model_orchestrator)
        self.context_compressor = ContextCompressor()
        self.self_correction = SelfCorrectionLoop()
        self.multi_model_router.set_tracer(self.execution_tracer)
        self.context_compressor.tracer = self.execution_tracer
        self.self_correction.tracer = self.execution_tracer
        self._setup_component_integration()

    def _setup_component_integration(self):
        self.tool_executor = self.tool_engine.execute_tool
        self.memory_retriever = None
        self.knowledge_searcher = None

    async def process_request(
        self,
        user_message: str,
        user_id: int,
        conversation_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        optimize_for: str = "balanced",
    ) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        trace = self.execution_tracer.start_trace(
            request_id=request_id,
            user_id=user_id,
            user_message=user_message,
            metadata={"conversation_id": conversation_id, "context": context},
        )
        try:
            intent = self.prompt_engine.detect_intent(user_message, context)
            task_type = self.model_orchestrator.detect_task_type(user_message, context)
            self.execution_tracer.trace_intent_detection(
                request_id, intent.value, confidence=0.9
            )

            if self.reliability and hasattr(self.reliability, "should_degrade"):
                if self.reliability.should_degrade():
                    optimize_for = "cost"

            routing_request = RoutingRequest(
                user_id=user_id,
                task_type=task_type.value,
                optimize_for=optimize_for,
                policy=RoutingPolicy.BALANCED,
                fallback_strategy=FallbackStrategy.CROSS_PROVIDER,
                requires_function_calling=True,
                trace=self.execution_tracer,
                request_id=request_id,
            )
            routing_result = await self.multi_model_router.route(routing_request)
            if not routing_result:
                raise Exception("No suitable model available")

            model_name = routing_result.model_id
            self.execution_tracer.trace_model_selection(
                request_id,
                model_name,
                reason=routing_result.reason,
                alternatives=routing_result.fallback_chain,
            )

            needs_plan = self.planning_engine.should_create_plan(user_message)
            if needs_plan:
                task_type_str = self.planning_engine.detect_task_type(user_message)
                plan = self.planning_engine.generate_plan(
                    goal=user_message,
                    task_type=task_type_str,
                    context=context,
                    show_to_user=True,
                    requires_approval=False,
                )
                self.execution_tracer.trace_plan_generation(
                    request_id,
                    plan.plan_id,
                    [step.to_dict() for step in plan.steps],
                )
                plan_result = await self.planning_engine.execute_plan(
                    plan.plan_id,
                    self.tool_executor,
                )
                self.execution_tracer.trace_plan_execution(
                    request_id,
                    plan.plan_id,
                    plan_result.get("success", False),
                )

            context_sources = self._assemble_context(
                user_id, conversation_id, user_message, context
            )
            self.execution_tracer.trace_context_retrieval(
                request_id,
                [s.source_type for s in context_sources],
                [s.metadata.get("document_id") for s in context_sources if s.metadata],
            )

            prompt_result = self.prompt_engine.construct_prompt(
                user_id=user_id,
                user_message=user_message,
                conversation_id=conversation_id,
                context_sources=context_sources,
                conversation_history=context.get("conversation_history") if context else None,
                user_preferences=user_preferences,
            )
            if not prompt_result.get("is_safe", True):
                raise Exception(f"Safety validation failed: {prompt_result.get('reason')}")

            full_prompt = prompt_result.get("full_prompt", "")
            token_count = self.context_compressor.estimate_tokens(full_prompt)
            max_context_tokens = routing_result.metadata.get("max_tokens", 4096) if routing_result else 4096
            if token_count > max_context_tokens:
                compressed = self.context_compressor.compress(
                    context=full_prompt,
                    max_tokens=max_context_tokens,
                    query=user_message,
                    strategy=CompressionStrategy.HYBRID,
                )
                full_prompt = compressed.compressed
                token_count = compressed.compressed_tokens

            await self.reasoning_pipeline.reason(
                user_message=user_message,
                user_id=user_id,
                context=context,
                tools=self.tool_engine.tools,
                memory_retriever=self.memory_retriever,
                knowledge_searcher=self.knowledge_searcher,
            )

            thinking = get_thinking_config(
                effort="medium",
                enabled=True,
                trace=self.execution_tracer,
                request_id=request_id,
            )
            thinking.add_step("understand", "Understand the user request and intent", confidence=0.9)
            thinking.add_step("plan", "Plan response structure and evidence", confidence=0.8)
            thinking.add_step("generate", "Generate the response", confidence=0.7)

            response_content = await self._generate_llm_response(
                prompt=full_prompt,
                model_name=model_name,
                request_id=request_id,
                routing_result=routing_result,
            )

            formatted_response = self.response_generator.generate_response(
                content=response_content,
                format=ResponseFormat.MARKDOWN,
                context={"task_type": task_type.value},
            )

            corrected = self.self_correction.review(
                response=formatted_response["content"],
                context=full_prompt,
                request_id=request_id,
            )
            if corrected.issues:
                formatted_response["content"] = corrected.corrected
                formatted_response["self_corrected"] = True

            estimated_tokens = self.context_compressor.estimate_tokens(formatted_response["content"]) + token_count
            estimated_cost = self.model_orchestrator.estimate_cost(
                model_name,
                estimated_tokens,
                estimated_tokens // 2,
            )
            self.cost_optimizer.track_execution(
                model_name=model_name,
                task_type=task_type.value,
                actual_tokens=estimated_tokens,
                actual_latency_ms=trace._calculate_duration() or 1000,
                actual_cost=estimated_cost,
            )
            self.execution_tracer.trace_response_generation(
                request_id,
                formatted_response["format"],
                estimated_tokens,
            )
            self.execution_tracer.end_trace(
                request_id,
                formatted_response["content"][:500],
            )
            return {
                "success": True,
                "request_id": request_id,
                "response": formatted_response["content"],
                "format": formatted_response["format"],
                "metadata": {
                    "model_used": model_name,
                    "intent_detected": intent.value,
                    "task_type": task_type.value,
                    "estimated_cost_usd": round(estimated_cost, 6),
                    "estimated_tokens": estimated_tokens,
                    "trace_id": request_id,
                    "fallback_used": routing_result.fallback_chain == [] and routing_result.model_id or False,
                    "self_corrected": corrected.issues != [],
                    "reasoning_summary": thinking.get_summary(),
                },
                "trace": trace.to_dict(),
            }

        except Exception as exc:
            self.execution_tracer.trace_error(
                request_id,
                str(exc),
                {"context": str(context)},
            )
            self.execution_tracer.end_trace(request_id, "")
            return {
                "success": False,
                "error": str(exc),
                "request_id": request_id,
                "trace": trace.to_dict(),
            }

    async def _generate_llm_response(
        self,
        prompt: str,
        model_name: str,
        request_id: str,
        routing_result: Any,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        provider = None
        for candidate in [routing_result.model_id] + routing_result.fallback_chain:
            provider = None
            try:
                from app.providers.factory import ProviderFactory
                provider = ProviderFactory.get_for_model(candidate)
                if not provider:
                    continue
                messages = []
                if prompt:
                    messages.append({"role": "user", "content": prompt})
                response = await provider.chat(
                    messages=[__import__("app.providers.base").providers.base.ChatMessage(role="user", content=prompt)],
                    model=candidate,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if candidate != routing_result.model_id:
                    self.execution_tracer.trace_model_fallback(
                        request_id=request_id,
                        from_model=routing_result.model_id,
                        to_model=candidate,
                        reason="Primary model failed; using fallback",
                    )
                return response.content or ""
            except Exception as exc:
                logger.warning("Model %s failed: %s", candidate, exc)
                self.execution_tracer.trace_error(
                    request_id=request_id,
                    error=str(exc),
                    context={"model": candidate, "stage": "llm_generation"},
                )
                continue
        return "[unavailable]"

    def _assemble_context(
        self,
        user_id: int,
        conversation_id: Optional[int],
        user_message: str,
        context: Optional[Dict[str, Any]],
    ) -> List[ContextSource]:
        sources = []
        if context and context.get("conversation_history"):
            sources.append(
                ContextSource(
                    source_type="conversation_history",
                    content=str(context["conversation_history"][-5:]),
                    relevance_score=0.9,
                    metadata={"conversation_id": conversation_id},
                )
            )
        if context and context.get("workspace_data"):
            sources.append(
                ContextSource(
                    source_type="workspace",
                    content=str(context["workspace_data"]),
                    relevance_score=0.8,
                    metadata={"workspace_id": context.get("workspace_id")},
                )
            )
        if context and context.get("files"):
            for file_info in context["files"]:
                sources.append(
                    ContextSource(
                        source_type="file",
                        content=f"File: {file_info.get('name')}",
                        relevance_score=0.7,
                        metadata={"file_id": file_info.get("id")},
                    )
                )
        return sources

    def get_available_models(self) -> List[Dict[str, Any]]:
        return self.model_orchestrator.list_available_models()

    def get_available_tools(self) -> List[Dict[str, Any]]:
        return self.tool_engine.list_tools()

    def get_execution_trace(self, request_id: str) -> Optional[Dict[str, Any]]:
        trace = self.execution_tracer.get_trace(request_id)
        if trace:
            return trace.to_dict()
        return None

    def get_cost_summary(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        return self.cost_optimizer.get_cost_summary(user_id)

    def get_optimization_suggestions(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.cost_optimizer.suggest_optimization(user_id)

    def set_user_model_preference(self, user_id: int, model_name: str):
        self.model_orchestrator.set_user_preference(user_id, model_name)

    def register_custom_tool(self, tool):
        self.tool_engine.register_tool(tool)

    def register_custom_model(self, model_id: str, config):
        self.model_orchestrator.register_model(model_id, config)
