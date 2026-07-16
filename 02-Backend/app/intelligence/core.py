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

This is the brain of Astrovox AI that transforms it from a simple chatbot
into an intelligent reasoning platform.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from .model_orchestrator import ModelOrchestrator, TaskType
from .prompt_engine import PromptEngine, ContextSource
from .reasoning_pipeline import ReasoningPipeline
from .tool_engine import ToolEngine
from .planning_engine import PlanningEngine
from .response_generator import ResponseGenerator, ResponseFormat
from .cost_optimizer import CostOptimizer, OptimizationStrategy
from .execution_tracer import ExecutionTracer, TraceEventType
from .reliability import ReliabilitySafeguards


class IntelligenceCore:
    """
    The central intelligence orchestration layer.
    Coordinates all components to provide intelligent reasoning and responses.
    """
    
    def __init__(self):
        # Initialize all components
        self.model_orchestrator = ModelOrchestrator()
        self.prompt_engine = PromptEngine()
        self.reasoning_pipeline = ReasoningPipeline()
        self.tool_engine = ToolEngine()
        self.planning_engine = PlanningEngine()
        self.response_generator = ResponseGenerator()
        self.cost_optimizer = CostOptimizer()
        self.execution_tracer = ExecutionTracer()
        self.reliability = ReliabilitySafeguards()
        
        # Component integration
        self._setup_component_integration()
    
    def _setup_component_integration(self):
        """Setup integration between components"""
        # Tool executor for planning engine
        self.tool_executor = self.tool_engine.execute_tool
        
        # Memory retriever (placeholder - will be implemented in Phase 3)
        self.memory_retriever = None
        
        # Knowledge searcher (placeholder - will be implemented in Phase 4)
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
        """
        Process a user request through the full intelligence pipeline.
        
        Args:
            user_message: The user's message
            user_id: User ID
            conversation_id: Conversation ID
            context: Additional context (files, workspace data, etc.)
            user_preferences: User-specific preferences
            optimize_for: Optimization strategy (cost, speed, quality, balanced)
        
        Returns:
            Complete response with metadata
        """
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        
        # Start execution trace
        trace = self.execution_tracer.start_trace(
            request_id=request_id,
            user_id=user_id,
            user_message=user_message,
            metadata={"conversation_id": conversation_id, "context": context},
        )
        
        try:
            # Step 1: Detect intent and task type
            intent = self.prompt_engine.detect_intent(user_message, context)
            task_type = self.model_orchestrator.detect_task_type(user_message, context)
            
            self.execution_tracer.trace_intent_detection(
                request_id, intent.value, confidence=0.9
            )
            
            # Step 2: Select optimal model
            model_config = self.model_orchestrator.select_model(
                task_type=task_type,
                user_id=user_id,
                optimize_for=optimize_for,
                requires_function_calling=True,
            )
            
            if not model_config:
                raise Exception("No suitable model available")
            
            self.execution_tracer.trace_model_selection(
                request_id,
                model_config.model_name,
                reason=f"Selected for task type: {task_type.value}",
            )
            
            # Step 3: Check if planning is needed
            needs_plan = self.planning_engine.should_create_plan(user_message)
            
            if needs_plan:
                # Generate execution plan
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
                
                # Execute plan
                plan_result = await self.planning_engine.execute_plan(
                    plan.plan_id,
                    self.tool_executor,
                )
                
                self.execution_tracer.trace_plan_execution(
                    request_id,
                    plan.plan_id,
                    plan_result.get("success", False),
                )
            
            # Step 4: Assemble context
            context_sources = self._assemble_context(
                user_id, conversation_id, user_message, context
            )
            
            self.execution_tracer.trace_context_retrieval(
                request_id,
                [s.source_type for s in context_sources],
                [s.metadata.get("document_id") for s in context_sources if s.metadata],
            )
            
            # Step 5: Construct prompt
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
            
            # Step 6: Execute reasoning pipeline
            reasoning_result = await self.reasoning_pipeline.reason(
                user_message=user_message,
                user_id=user_id,
                context=context,
                tools=self.tool_engine.tools,
                memory_retriever=self.memory_retriever,
                knowledge_searcher=self.knowledge_searcher,
            )
            
            # Step 7: Generate response
            # In a real implementation, this would call the LLM
            # For now, we'll generate a placeholder response
            response_content = self._generate_llm_response(
                prompt_result["full_prompt"],
                model_config.model_name,
            )
            
            # Step 8: Format response
            formatted_response = self.response_generator.generate_response(
                content=response_content,
                format=ResponseFormat.MARKDOWN,
                context={"task_type": task_type.value},
            )
            
            # Step 9: Track execution metrics
            estimated_tokens = len(response_content.split()) + len(user_message.split())
            estimated_cost = self.model_orchestrator.estimate_cost(
                model_config.model_name,
                estimated_tokens,
                estimated_tokens // 2,
            )
            
            self.cost_optimizer.track_execution(
                model_name=model_config.model_name,
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
            
            # End trace
            self.execution_tracer.end_trace(
                request_id,
                formatted_response["content"][:500],
            )
            
            # Return complete response
            return {
                "success": True,
                "request_id": request_id,
                "response": formatted_response["content"],
                "format": formatted_response["format"],
                "metadata": {
                    "model_used": model_config.model_name,
                    "intent_detected": intent.value,
                    "task_type": task_type.value,
                    "estimated_cost_usd": round(estimated_cost, 6),
                    "estimated_tokens": estimated_tokens,
                    "trace_id": request_id,
                },
                "trace": trace.to_dict(),
            }
        
        except Exception as e:
            # Trace error
            self.execution_tracer.trace_error(
                request_id,
                str(e),
                {"context": str(context)},
            )
            self.execution_tracer.end_trace(request_id, "")
            
            return {
                "success": False,
                "error": str(e),
                "request_id": request_id,
                "trace": trace.to_dict(),
            }
    
    def _assemble_context(
        self,
        user_id: int,
        conversation_id: Optional[int],
        user_message: str,
        context: Optional[Dict[str, Any]],
    ) -> List[ContextSource]:
        """Assemble context from multiple sources"""
        sources = []
        
        # Add conversation context if available
        if context and context.get("conversation_history"):
            sources.append(
                ContextSource(
                    source_type="conversation_history",
                    content=str(context["conversation_history"][-5:]),
                    relevance_score=0.9,
                    metadata={"conversation_id": conversation_id},
                )
            )
        
        # Add workspace context if available
        if context and context.get("workspace_data"):
            sources.append(
                ContextSource(
                    source_type="workspace",
                    content=str(context["workspace_data"]),
                    relevance_score=0.8,
                    metadata={"workspace_id": context.get("workspace_id")},
                )
            )
        
        # Add file context if available
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
    
    def _generate_llm_response(
        self,
        prompt: str,
        model_name: str,
    ) -> str:
        """
        Generate LLM response (placeholder).
        
        In production, this would call the actual LLM API.
        For now, returns a placeholder response.
        """
        # This is a placeholder. In production, integrate with:
        # - OpenAI API
        # - Anthropic API
        # - Google API
        # - Local models via Ollama
        
        return f"[Response from {model_name}]\n\nThis is a placeholder response. In production, this would be generated by the actual LLM model based on the constructed prompt."
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        return self.model_orchestrator.list_available_models()
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return self.tool_engine.list_tools()
    
    def get_execution_trace(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get execution trace for a request"""
        trace = self.execution_tracer.get_trace(request_id)
        if trace:
            return trace.to_dict()
        return None
    
    def get_cost_summary(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get cost summary"""
        return self.cost_optimizer.get_cost_summary(user_id)
    
    def get_optimization_suggestions(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get optimization suggestions"""
        return self.cost_optimizer.suggest_optimization(user_id)
    
    def set_user_model_preference(self, user_id: int, model_name: str):
        """Set user's preferred model"""
        self.model_orchestrator.set_user_preference(user_id, model_name)
    
    def register_custom_tool(self, tool):
        """Register a custom tool"""
        self.tool_engine.register_tool(tool)
    
    def register_custom_model(self, model_id: str, config):
        """Register a custom model"""
        self.model_orchestrator.register_model(model_id, config)
