"""
Cost & Performance Optimizer - Phase 2.12

Selects the most efficient execution strategy by optimizing for:
- Lowest cost
- Fastest response
- Highest accuracy
- Lowest token usage
- Best available model

Provides metrics such as:
- Estimated cost
- Tokens consumed
- Execution time
- Model used
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
import time


class OptimizationStrategy(Enum):
    """Optimization strategies"""
    COST = "cost"  # Minimize cost
    SPEED = "speed"  # Minimize latency
    QUALITY = "quality"  # Maximize quality
    BALANCED = "balanced"  # Balance all factors
    TOKENS = "tokens"  # Minimize token usage


class CostOptimizer:
    """
    Optimizes model selection and execution strategy based on
    cost, performance, and quality requirements.
    """
    
    def __init__(self):
        self.execution_history: List[Dict[str, Any]] = []
        self.model_performance_cache: Dict[str, Dict[str, Any]] = {}
    
    def optimize_execution(
        self,
        available_models: List[Dict[str, Any]],
        task_type: str,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Select the optimal model and execution strategy.
        
        Args:
            available_models: List of available models with metadata
            task_type: Type of task to perform
            strategy: Optimization strategy to use
            constraints: Optional constraints (max_cost, max_latency, etc.)
        
        Returns:
            Optimization recommendation
        """
        constraints = constraints or {}
        
        # Filter models by constraints
        filtered_models = self._filter_by_constraints(available_models, constraints)
        
        if not filtered_models:
            return {
                "success": False,
                "error": "No models meet the specified constraints",
            }
        
        # Score models based on strategy
        scored_models = self._score_models(filtered_models, task_type, strategy)
        
        # Select best model
        best_model = max(scored_models, key=lambda x: x["score"])
        
        # Estimate execution metrics
        estimates = self._estimate_execution(best_model, task_type)
        
        return {
            "success": True,
            "recommended_model": best_model,
            "strategy": strategy.value,
            "estimates": estimates,
            "alternatives": scored_models[:3],  # Top 3 alternatives
        }
    
    def _filter_by_constraints(
        self,
        models: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Filter models by constraints"""
        filtered = []
        
        for model in models:
            # Check max cost constraint
            if "max_cost" in constraints:
                estimated_cost = model.get("cost_per_1k_input", 0) + model.get("cost_per_1k_output", 0)
                if estimated_cost > constraints["max_cost"]:
                    continue
            
            # Check max latency constraint
            if "max_latency" in constraints:
                latency = model.get("avg_latency_ms", 0)
                if latency > constraints["max_latency"]:
                    continue
            
            # Check min context size
            if "min_context" in constraints:
                max_tokens = model.get("max_tokens", 0)
                if max_tokens < constraints["min_context"]:
                    continue
            
            # Check required features
            if "requires_vision" in constraints and constraints["requires_vision"]:
                if not model.get("supports_vision", False):
                    continue
            
            if "requires_function_calling" in constraints and constraints["requires_function_calling"]:
                if not model.get("supports_function_calling", False):
                    continue
            
            filtered.append(model)
        
        return filtered
    
    def _score_models(
        self,
        models: List[Dict[str, Any]],
        task_type: str,
        strategy: OptimizationStrategy,
    ) -> List[Dict[str, Any]]:
        """Score models based on strategy"""
        scored = []
        
        for model in models:
            score = self._calculate_score(model, task_type, strategy)
            scored.append({**model, "score": score})
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        return scored
    
    def _calculate_score(
        self,
        model: Dict[str, Any],
        task_type: str,
        strategy: OptimizationStrategy,
    ) -> float:
        """Calculate a score for a model based on strategy"""
        
        # Get model metrics
        cost = model.get("cost_per_1k_input", 0) + model.get("cost_per_1k_output", 0)
        latency = model.get("avg_latency_ms", 1000)
        max_tokens = model.get("max_tokens", 4096)
        supports_function_calling = model.get("supports_function_calling", False)
        
        # Base score
        score = 0.0
        
        if strategy == OptimizationStrategy.COST:
            # Lower cost is better
            score = 100.0 / (cost + 0.01)
        
        elif strategy == OptimizationStrategy.SPEED:
            # Lower latency is better
            score = 10000.0 / (latency + 1)
        
        elif strategy == OptimizationStrategy.QUALITY:
            # Higher context and function calling support is better
            score = (max_tokens / 1000.0) * 10
            if supports_function_calling:
                score += 20
        
        elif strategy == OptimizationStrategy.TOKENS:
            # Higher max tokens is better
            score = max_tokens / 100.0
        
        elif strategy == OptimizationStrategy.BALANCED:
            # Balance all factors
            cost_score = 50.0 / (cost + 0.01)
            speed_score = 5000.0 / (latency + 1)
            quality_score = (max_tokens / 1000.0) * 5
            if supports_function_calling:
                quality_score += 10
            
            score = (cost_score + speed_score + quality_score) / 3.0
        
        # Apply task-specific adjustments
        if task_type in ["coding", "research", "document_analysis"]:
            # These tasks benefit from larger context
            if max_tokens > 100000:
                score *= 1.2
        
        return score
    
    def _estimate_execution(
        self,
        model: Dict[str, Any],
        task_type: str,
    ) -> Dict[str, Any]:
        """Estimate execution metrics"""
        
        # Estimate token usage based on task type
        token_estimates = {
            "general_chat": {"input": 500, "output": 300},
            "coding": {"input": 1000, "output": 800},
            "mathematics": {"input": 300, "output": 200},
            "research": {"input": 800, "output": 600},
            "document_analysis": {"input": 2000, "output": 1000},
            "summarization": {"input": 1500, "output": 300},
        }
        
        tokens = token_estimates.get(task_type, {"input": 500, "output": 300})
        
        # Calculate cost
        cost_per_1k_input = model.get("cost_per_1k_input", 0)
        cost_per_1k_output = model.get("cost_per_1k_output", 0)
        
        estimated_cost = (
            (tokens["input"] / 1000) * cost_per_1k_input +
            (tokens["output"] / 1000) * cost_per_1k_output
        )
        
        # Estimate latency
        base_latency = model.get("avg_latency_ms", 1000)
        # Add processing time based on token count
        processing_time = (tokens["input"] + tokens["output"]) / 100  # rough estimate
        estimated_latency_ms = base_latency + processing_time
        
        return {
            "estimated_cost_usd": round(estimated_cost, 6),
            "estimated_input_tokens": tokens["input"],
            "estimated_output_tokens": tokens["output"],
            "estimated_total_tokens": tokens["input"] + tokens["output"],
            "estimated_latency_ms": round(estimated_latency_ms),
            "estimated_latency_seconds": round(estimated_latency_ms / 1000, 2),
        }
    
    def track_execution(
        self,
        model_name: str,
        task_type: str,
        actual_tokens: int,
        actual_latency_ms: int,
        actual_cost: float,
    ):
        """
        Track actual execution metrics for learning and optimization.
        
        Args:
            model_name: Name of the model used
            task_type: Type of task performed
            actual_tokens: Actual tokens consumed
            actual_latency_ms: Actual latency in milliseconds
            actual_cost: Actual cost in USD
        """
        execution_record = {
            "model_name": model_name,
            "task_type": task_type,
            "tokens": actual_tokens,
            "latency_ms": actual_latency_ms,
            "cost_usd": actual_cost,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.execution_history.append(execution_record)
        
        # Update performance cache
        if model_name not in self.model_performance_cache:
            self.model_performance_cache[model_name] = {
                "total_executions": 0,
                "total_tokens": 0,
                "total_latency_ms": 0,
                "total_cost": 0,
                "task_types": {},
            }
        
        cache = self.model_performance_cache[model_name]
        cache["total_executions"] += 1
        cache["total_tokens"] += actual_tokens
        cache["total_latency_ms"] += actual_latency_ms
        cache["total_cost"] += actual_cost
        
        if task_type not in cache["task_types"]:
            cache["task_types"][task_type] = {
                "count": 0,
                "avg_tokens": 0,
                "avg_latency_ms": 0,
            }
        
        task_cache = cache["task_types"][task_type]
        task_cache["count"] += 1
        task_cache["avg_tokens"] = (
            (task_cache["avg_tokens"] * (task_cache["count"] - 1) + actual_tokens) /
            task_cache["count"]
        )
        task_cache["avg_latency_ms"] = (
            (task_cache["avg_latency_ms"] * (task_cache["count"] - 1) + actual_latency_ms) /
            task_cache["count"]
        )
    
    def get_model_performance(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get performance statistics for a model"""
        cache = self.model_performance_cache.get(model_name)
        if not cache:
            return None
        
        return {
            "model_name": model_name,
            "total_executions": cache["total_executions"],
            "average_tokens": cache["total_tokens"] / cache["total_executions"],
            "average_latency_ms": cache["total_latency_ms"] / cache["total_executions"],
            "total_cost_usd": cache["total_cost"],
            "average_cost_usd": cache["total_cost"] / cache["total_executions"],
            "task_types": cache["task_types"],
        }
    
    def get_cost_summary(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get cost summary for a user or overall"""
        # Filter by user_id if provided (would need user_id in execution records)
        relevant_history = self.execution_history
        
        if not relevant_history:
            return {
                "total_executions": 0,
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "average_latency_ms": 0,
            }
        
        total_cost = sum(r["cost_usd"] for r in relevant_history)
        total_tokens = sum(r["tokens"] for r in relevant_history)
        total_latency = sum(r["latency_ms"] for r in relevant_history)
        
        return {
            "total_executions": len(relevant_history),
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "average_latency_ms": round(total_latency / len(relevant_history)),
            "by_model": self._get_summary_by_model(relevant_history),
            "by_task_type": self._get_summary_by_task(relevant_history),
        }
    
    def _get_summary_by_model(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary grouped by model"""
        summary = {}
        for record in history:
            model = record["model_name"]
            if model not in summary:
                summary[model] = {
                    "count": 0,
                    "cost": 0.0,
                    "tokens": 0,
                }
            summary[model]["count"] += 1
            summary[model]["cost"] += record["cost_usd"]
            summary[model]["tokens"] += record["tokens"]
        
        return summary
    
    def _get_summary_by_task(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary grouped by task type"""
        summary = {}
        for record in history:
            task = record["task_type"]
            if task not in summary:
                summary[task] = {
                    "count": 0,
                    "cost": 0.0,
                    "tokens": 0,
                }
            summary[task]["count"] += 1
            summary[task]["cost"] += record["cost_usd"]
            summary[task]["tokens"] += record["tokens"]
        
        return summary
    
    def suggest_optimization(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Suggest optimizations based on execution history.
        
        Args:
            user_id: Optional user ID for user-specific suggestions
        
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        if not self.execution_history:
            suggestions.append({
                "type": "info",
                "message": "No execution history available for optimization suggestions.",
            })
            return suggestions
        
        summary = self.get_cost_summary(user_id)
        
        # Check for high-cost models
        by_model = summary.get("by_model", {})
        for model, data in by_model.items():
            avg_cost = data["cost"] / data["count"]
            if avg_cost > 0.01:  # More than 1 cent per request
                suggestions.append({
                    "type": "cost",
                    "message": f"Model {model} has high average cost (${avg_cost:.4f}). Consider using a cheaper model for similar tasks.",
                    "model": model,
                    "current_avg_cost": avg_cost,
                })
        
        # Check for high latency
        by_task = summary.get("by_task_type", {})
        for task, data in by_task.items():
            if data["count"] > 10:  # Only suggest if we have enough data
                suggestions.append({
                    "type": "performance",
                    "message": f"Task type '{task}' has been executed {data['count']} times. Consider caching results if applicable.",
                    "task_type": task,
                    "execution_count": data["count"],
                })
        
        if not suggestions:
            suggestions.append({
                "type": "info",
                "message": "Current usage looks optimized. No specific suggestions at this time.",
            })
        
        return suggestions
